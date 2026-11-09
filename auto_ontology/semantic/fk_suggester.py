"""LLM inference for columns that look like foreign keys."""

import logging
from pathlib import Path
from typing import Any

from auto_ontology.semantic.deterministic import fk_source_columns
from auto_ontology.utils.llm_invoke import (
    get_llm_client,
    invoke_with_structured_output,
)
from auto_ontology.utils.prompt_loader import load_chat_prompt_template
from auto_ontology.utils.sample_values import stringify_sample_values
from auto_ontology.semantic.models import (
    FkAndPkResult,
    PotentialFkResult,
    PotentialFkSuggestion,
)

logger = logging.getLogger(__name__)

_PROMPT = load_chat_prompt_template(
    Path(__file__).with_name("prompts.yaml"), "fk_suggester"
)


def _pk_column_names(table: dict[str, Any]) -> set[str]:
    pk = table.get("pk") or []
    if isinstance(pk, str):
        return {pk} if pk else set()
    return {str(name) for name in pk if name}


def _candidate_columns(
    columns: list[dict[str, Any]],
    *,
    excluded: set[str],
) -> list[dict[str, Any]]:
    return [
        col
        for col in columns
        if (name := col.get("name"))
        and name not in excluded
        and not col.get("is_foreign_key_target")
    ]


def _format_sample_values(raw: Any) -> str:
    """Return a 'samples: ...' string filtered to ≤30-char values, or empty."""
    values = stringify_sample_values(raw, max_len=30)
    if not values:
        return ""
    return "samples: " + ", ".join(values)


def _format_column_line(col: dict[str, Any], is_unique: bool | None = None) -> str:
    desc = col.get("description") or ""
    suffix = f" — {desc}" if desc else ""
    sample_str = _format_sample_values(col.get("sample_values"))
    if sample_str:
        suffix += f" [{sample_str}]"
    if is_unique is not None:
        suffix += f" [is_unique: {str(is_unique).lower()}]"
    return f"  - {col['name']} ({col.get('data_type', '')}){suffix}"


def suggest_potential_foreign_keys(
    table: dict[str, Any],
    ctx: dict[str, Any],
    columns_profiling_samples: dict[str, dict[str, Any]] | None = None,
) -> PotentialFkResult:
    """Ask the LLM which non-PK, non-declared-FK columns may be foreign keys.

    *columns_profiling_samples* maps each column to its profiling data
    (``{"sample_values": [...], "is_unique": bool}``) when a live sample was
    available. Columns referenced by declared foreign keys are not candidates:
    they identify rows in this table rather than referencing another table.
    """
    columns = ctx.get("columns", [])
    fks = ctx.get("fks", [])
    pk_names = _pk_column_names(table)
    known_fk_names = fk_source_columns(fks)
    excluded = pk_names | known_fk_names
    candidates = _candidate_columns(columns, excluded=excluded)

    # A payload-bearing junction can have no FK-suggestion candidates because
    # all of its key columns are already declared. Tables wider than two
    # columns still need the table-grain decision from this same LLM call.
    if not candidates and len(columns) <= 2:
        return PotentialFkResult()

    schema_name = table.get("schema_name") or ""
    table_header = f"{schema_name}.{table['name']}" if schema_name else table["name"]
    known_fk_block = ", ".join(sorted(known_fk_names)) if known_fk_names else "(none)"
    pk_block = ", ".join(sorted(pk_names)) if pk_names else "(none)"
    profiling = columns_profiling_samples or {}
    all_column_lines = "\n".join(
        _format_column_line(col, (profiling.get(col["name"]) or {}).get("is_unique"))
        for col in columns
        if col.get("name")
    )
    candidate_lines = (
        "\n".join(
            _format_column_line(
                col, (profiling.get(col["name"]) or {}).get("is_unique")
            )
            for col in candidates
        )
        or "  (none)"
    )
    known_fk_lines = (
        "\n".join(
            (
                f"  - {fk.get('source_column')} -> "
                f"{fk.get('target_table') or fk.get('target_table_id') or '(unknown target)'}"
            )
            for fk in fks
            if fk.get("source_column")
        )
        or "  (none)"
    )

    messages = _PROMPT.format_messages(
        table_header=table_header,
        description=table.get("description") or "",
        pk_block=pk_block,
        known_fk_block=known_fk_block,
        known_fk_lines=known_fk_lines,
        all_column_lines=all_column_lines,
        candidate_lines=candidate_lines,
    )

    result = invoke_with_structured_output(
        get_llm_client(temperature=0.0), messages, FkAndPkResult
    )
    if result is None:
        return PotentialFkResult()

    llm_pk_names = {
        name
        for raw_name in result.pk_column_names
        if (name := raw_name.strip())
        and (profiling.get(name) or {}).get("is_unique") is not False
    }
    allowed = {col["name"] for col in candidates}
    filtered: list[PotentialFkSuggestion] = []
    seen: set[str] = set()
    for item in result.fk_suggestions:
        name = item.column_name.strip()
        if not name or name in seen or name not in allowed:
            continue
        seen.add(name)
        filtered.append(
            PotentialFkSuggestion(column_name=name, rationale=item.rationale.strip())
        )
    for col in candidates:
        name = col.get("name", "")
        if name in seen:
            continue
        is_unique = (profiling.get(name) or {}).get("is_unique")
        if (
            (col.get("data_type") or "").lower() == "uuid"
            and name not in llm_pk_names
            and is_unique is False
        ):
            seen.add(name)
            filtered.append(
                PotentialFkSuggestion(
                    column_name=name,
                    rationale=(
                        "uuid type, not a declared or inferred primary key — "
                        "almost certainly references another entity"
                    ),
                )
            )

    return PotentialFkResult(
        suggestions=filtered,
        is_junction_table=result.is_junction_table,
        junction_table_rationale=result.junction_table_rationale.strip(),
    )
