"""LLM Term extraction — names and column display-name assignments only."""

import re
from pathlib import Path
from typing import Any

from auto_ontology.semantic.deterministic import to_term_name
from auto_ontology.semantic.domain import DomainSummary
from auto_ontology.utils.llm_invoke import (
    get_llm_client,
    invoke_with_structured_output,
)
from auto_ontology.utils.prompt_loader import load_chat_prompt_template, load_prompt
from pydantic import BaseModel, ConfigDict, Field

from auto_ontology.semantic.models import (
    ColumnAttributeSpec,
    RawTableTermsResult,
    TableTermsResult,
    TermAttributeAssignment,
    TermProposal,
)

_INVALID = {
    "unnamed",
    "unknown",
    "none",
    "",
    "tanpa nama",
    "tidak diketahui",
    "tidak ada",
}
# A hyphen may join words: Indonesian reduplication ("Rata-rata") is one word, and
# rejecting it would replace a good label with one derived from the physical name.
_LABEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(?:[ -][A-Za-z][A-Za-z0-9]*)*$")

_PROMPTS_FILE = Path(__file__).with_name("prompts.yaml")
_PROMPT = load_chat_prompt_template(_PROMPTS_FILE, "term_extractor")
_DOMAIN_BLOCK = load_prompt("term_extractor", _PROMPTS_FILE)["sections"]["domain_block"]


class _SynonymExtractionModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    synonyms: list[str] = Field(
        default_factory=list,
        description=(
            "Abbreviations, acronyms, or alternate names explicitly written in the "
            "description. Empty list if none are stated."
        ),
    )


_SYNONYM_PROMPT = load_chat_prompt_template(_PROMPTS_FILE, "term_synonyms")


def _normalize_label(name: str, *, fallback: str) -> str:
    cleaned = name.strip()
    if cleaned.lower() in _INVALID or not _LABEL_RE.match(cleaned):
        return fallback
    # to_term_name splits on every non-alphanumeric, so apply it between hyphens.
    return "-".join(to_term_name(piece) for piece in cleaned.split("-"))


def _format_spec_line(spec: ColumnAttributeSpec) -> str:
    desc = f" — {spec.description}" if spec.description else ""
    return f"  - source_column={spec.source_column} ({spec.datatype}){desc}"


def apply_display_names_to_specs(
    table_result: TableTermsResult,
    specs: list[ColumnAttributeSpec],
) -> None:
    """Write LLM display labels back onto column specs for downstream merges."""
    by_column = {spec.source_column: spec for spec in specs}
    for term in table_result.terms:
        for attr in term.attributes:
            spec = by_column.get(attr.source_column)
            if spec is not None:
                spec.display_name = attr.display_name
    for spec in specs:
        if not spec.display_name:
            spec.display_name = spec.name


def _fallback_result(
    table: dict[str, Any],
    specs: list[ColumnAttributeSpec],
) -> TableTermsResult:
    name = to_term_name(table["name"])
    attributes = [
        TermAttributeAssignment(
            source_column=spec.source_column,
            display_name=spec.name,
        )
        for spec in specs
    ]
    result = TableTermsResult(
        terms=[
            TermProposal(
                name=name,
                description=f"Entitas bisnis yang diwakili tabel {table['name']}",
                attributes=attributes,
            )
        ]
    )
    apply_display_names_to_specs(result, specs)
    return result


def _sanitize_result(
    result: RawTableTermsResult,
    *,
    table: dict[str, Any],
    specs: list[ColumnAttributeSpec],
) -> TableTermsResult:
    spec_by_column = {spec.source_column: spec for spec in specs}
    allowed_columns = set(spec_by_column)
    default_term = to_term_name(table["name"])

    sanitized_terms: list[TermProposal] = []
    seen_term_names: set[str] = set()
    assigned_columns: set[str] = set()

    for raw_term in result.terms:
        term_name = _normalize_label(raw_term.name, fallback=default_term)
        if term_name in seen_term_names:
            continue
        seen_term_names.add(term_name)

        attributes: list[TermAttributeAssignment] = []
        for raw_attr in raw_term.attributes:
            source_column = raw_attr.source_column.strip()
            if (
                not source_column
                or source_column not in allowed_columns
                or source_column in assigned_columns
            ):
                continue
            spec = spec_by_column[source_column]
            attributes.append(
                TermAttributeAssignment(
                    source_column=source_column,
                    display_name=_normalize_label(
                        raw_attr.display_name,
                        fallback=spec.name,
                    ),
                )
            )
            assigned_columns.add(source_column)

        sanitized_terms.append(
            TermProposal(
                name=term_name,
                description=raw_term.description.strip(),
                attributes=attributes,
            )
        )

    if not sanitized_terms:
        return _fallback_result(table, specs)

    # Any unassigned columns fall back to the first Term.
    primary = sanitized_terms[0]
    for spec in specs:
        if spec.source_column not in assigned_columns:
            primary.attributes.append(
                TermAttributeAssignment(
                    source_column=spec.source_column,
                    display_name=spec.name,
                )
            )
            assigned_columns.add(spec.source_column)

    table_result = TableTermsResult(terms=sanitized_terms)
    apply_display_names_to_specs(table_result, specs)
    return table_result


def _extract_synonyms(description: str) -> list[str]:
    """Dedicated LLM call to extract alternate names from a table description."""
    if not description:
        return []
    result = invoke_with_structured_output(
        get_llm_client(temperature=0.0, max_tokens=1024),
        _SYNONYM_PROMPT.format_messages(description=description),
        _SynonymExtractionModel,
    )
    if result is None:
        return []
    return [s.strip() for s in result.synonyms if s.strip()]


def extract_term(
    table: dict[str, Any],
    ctx: dict[str, Any],
    specs: list[ColumnAttributeSpec],
    *,
    domain_summary: DomainSummary | None = None,
) -> TableTermsResult:
    """Propose one or more Terms and assign candidate column attributes to each."""
    if not specs:
        return _fallback_result(table, specs)

    description = table.get("description") or ""

    spec_lines = "\n".join(_format_spec_line(spec) for spec in specs[:40])
    domain_block = ""
    if domain_summary:
        domain_block = _DOMAIN_BLOCK.format(
            domains=", ".join(domain_summary.domains[:8]),
            core_entities=", ".join(domain_summary.core_entities[:12]),
        )
    messages = _PROMPT.format_messages(
        table_name=table["name"],
        description=description,
        spec_lines=spec_lines,
        domain_block=domain_block,
    )
    result = invoke_with_structured_output(
        get_llm_client(temperature=0.0, max_tokens=4096),
        messages,
        RawTableTermsResult,
    )
    if result is None:
        return _fallback_result(table, specs)

    table_result = _sanitize_result(result, table=table, specs=specs)

    synonyms = _extract_synonyms(description)
    if synonyms:
        for term in table_result.terms:
            term.synonyms = synonyms

    return table_result
