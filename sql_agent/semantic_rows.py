# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Match a topic against row text by meaning, using the warehouse's vector columns.

Ported from ``classic_sql_agent``. A keyword filter misses a topic worded differently
in the data, so this pre-fetches the matching row ids and hands them to SQL generation
through a placeholder: ids never pass through the LLM, and the generation prompt stays
the original one because the instruction travels as evidence.

The classic node kept at most 20 ids, which silently undercounted larger topics. This
one verifies more candidates and reports when even those may not be all of them.
"""

from __future__ import annotations

import logging
import numbers
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from auto_ontology.retrieval.text_to_sql.base import BaseAgent, record_thought
from auto_ontology.retrieval.text_to_sql.connector_routing import (
    resolve_connector_from_tables,
)
from auto_ontology.retrieval.text_to_sql.state import (
    AgentState,
    get_standalone_question,
)
from auto_ontology.utils.embedding import embed_texts, get_embed_params
from auto_ontology.utils.llm_invoke import invoke_with_structured_output
from auto_ontology.utils.prompt_loader import load_chat_prompt_template
from auto_ontology.utils.rerank import get_rerank_kwargs, rerank_hits
from auto_ontology.utils.sql_identifiers import quoted_identifier

logger = logging.getLogger(__name__)

_NODE_NAME = "semantic_rows"
# Recorded when more rows may match than were reviewed; the service reports it.
SEMANTIC_TRUNCATED_NOTE = "semantic_search_truncated"
_VECTOR_SUFFIX = "_vector"
RECALL_K = 100
VERIFY_K = 50
SNIPPET_CHARS = 200
SEARCH_TIMEOUT_S = 20.0

_PROMPTS_FILE = Path(__file__).with_name("prompts.yaml")
_PLANNER_PROMPT = load_chat_prompt_template(_PROMPTS_FILE, "semantic_planner")
_VERIFIER_PROMPT = load_chat_prompt_template(_PROMPTS_FILE, "semantic_verifier")


class SemanticFilter(BaseModel):
    table: str = Field(description="Table that owns the searchable column.")
    column: str = Field(description="Searchable column name, exactly as listed.")
    query: str = Field(description="Core phrase plus close synonyms or subtopics.")


class SemanticPlan(BaseModel):
    filters: list[SemanticFilter] = Field(default_factory=list)


class RelevantCandidates(BaseModel):
    reasoning: str = Field(
        description="One short line per matching candidate: '<number>: <why>'."
    )
    numbers: list[int] = Field(
        description="Numbers of the candidates that genuinely match. Empty if none."
    )


def searchable_columns(tables: list[dict[str, Any]]) -> dict[tuple[str, str], dict]:
    """Map ``(table, vector column)`` to what a search on it needs.

    A column qualifies when it is a ``vector`` named after a text column in the same
    table, and the table has a single-column primary key to hand back as the id.
    """
    found: dict[tuple[str, str], dict] = {}
    for table in tables:
        keys = table.get("pk") or []
        columns = {c.get("name"): c for c in table.get("columns") or []}
        if len(keys) != 1:
            continue
        for name, column in columns.items():
            source = (name or "").removesuffix(_VECTOR_SUFFIX)
            if (
                source != name
                and source in columns
                and str(column.get("data_type") or "") == "vector"
            ):
                found[(table.get("name"), name)] = {
                    "table": table,
                    "pk": keys[0],
                    "source": source,
                    "description": columns[source].get("description") or "",
                }
    return found


def _nearest_rows(
    connector: Any, spec: dict, column: str, vector: list[float]
) -> list[dict]:
    table = spec["table"]
    pk = quoted_identifier(spec["pk"], "postgres")
    source = quoted_identifier(spec["source"], "postgres")
    target = quoted_identifier(column, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    frame = connector.execute(
        f"SELECT {pk} AS id, left({source}::text, {SNIPPET_CHARS}) AS snippet "
        f"FROM {relation} WHERE {target} IS NOT NULL "
        f"ORDER BY {target} <=> %s::vector LIMIT %s",
        [str(vector), RECALL_K],
        timeout_s=SEARCH_TIMEOUT_S,
    )
    return frame.to_dict("records") if len(frame) else []


def _best_candidates(query: str, rows: list[dict]) -> list[dict]:
    """Rerank when a reranker is configured, otherwise keep the vector order."""
    if len(rows) <= 1:
        return rows
    try:
        return rerank_hits(
            query, rows, **get_rerank_kwargs(), top_n=VERIFY_K, text_key="snippet"
        )
    except Exception:  # noqa: BLE001 — ranking is an optimization, not a requirement
        logger.warning("Rerank failed; keeping vector order", exc_info=True)
        return rows[:VERIFY_K]


def _verified_ids(llm: Any, topic: str, candidates: list[dict]) -> list[Any]:
    if not candidates:
        return []
    listing = "\n".join(
        f"{number}. {' '.join(str(row.get('snippet') or '').split())}"
        for number, row in enumerate(candidates, 1)
    )
    messages = _VERIFIER_PROMPT.format_messages(topic=topic, candidates=listing)
    result = invoke_with_structured_output(llm, messages, RelevantCandidates)
    if result is None:
        raise ValueError("The semantic verifier returned no result.")
    numbers = dict.fromkeys(n for n in result.numbers if 1 <= n <= len(candidates))
    return [candidates[n - 1]["id"] for n in numbers]


def sql_literal(value: Any) -> str:
    if isinstance(value, numbers.Integral):
        return str(int(value))
    return "'" + str(value).replace("'", "''") + "'"


def _matches_context(matches: list[tuple[SemanticFilter, dict, list[Any]]]) -> str:
    lines = ["Topic filters already matched by meaning:"]
    for number, (found, spec, ids) in enumerate(matches, 1):
        table = spec["table"]
        lines.append(
            f'- Topic "{found.query}" on "{table.get("schema_name")}"."{found.table}".'
            f'"{spec["source"]}" matched {len(ids)} row(s). Use exactly this filter: '
            f'"{found.table}"."{spec["pk"]}" IN (__SEMANTIC_{number}__)'
        )
    lines.append(
        "Write that IN condition verbatim, including the __SEMANTIC_n__ placeholder, "
        "which is replaced with the matching ids automatically. Do not add ILIKE or "
        "LIKE on that column for the same topic. For listing questions, also select "
        "the source column."
    )
    return "\n".join(lines)


def _fallback_context(
    filters: list[SemanticFilter], specs: dict[tuple[str, str], dict]
) -> str:
    lines = ["Meaning-based search is unavailable right now. For these topics:"]
    for found in filters:
        source = specs[(found.table, found.column)]["source"]
        lines.append(
            f'- "{found.query}": filter "{found.table}"."{source}" with ILIKE on the '
            "core keywords, combined with OR across synonyms."
        )
    return "\n".join(lines)


def _with_evidence(state: AgentState, addition: str) -> str:
    existing = (state.get("evidence") or "").strip()
    return f"{existing}\n\n{addition}" if existing else addition


class SemanticRowsAgent(BaseAgent):
    """Pre-fetch row ids for topic constraints in the question."""

    def __init__(self) -> None:
        super().__init__(_NODE_NAME)

    def execute(self, state: AgentState) -> dict[str, Any]:
        path_state = state.get("path_state", {})
        path_state["semantic_ids"] = {}
        tables = path_state.get("relevant_tables") or []
        specs = searchable_columns(tables)
        if not specs:
            return {"path_state": path_state}

        llm = state["llm"]
        columns = "\n".join(
            f"- {table}.{column}: {spec['description'] or spec['source']}"
            for (table, column), spec in specs.items()
        )
        messages = _PLANNER_PROMPT.format_messages(
            question=get_standalone_question(state), columns=columns
        )
        plan = invoke_with_structured_output(llm, messages, SemanticPlan)
        filters = [
            found
            for found in (plan.filters if plan else [])
            if (found.table, found.column) in specs and found.query.strip()
        ]
        if not filters:
            return {"path_state": path_state}

        try:
            matches, ids_by_placeholder = self._search(state, filters, specs, tables)
        except Exception:  # noqa: BLE001 — degrade to keywords rather than fail the run
            self.logger.warning("Semantic search failed", exc_info=True)
            return {
                "path_state": path_state,
                "evidence": _with_evidence(state, _fallback_context(filters, specs)),
            }
        path_state["semantic_ids"] = ids_by_placeholder
        return {
            "path_state": path_state,
            "evidence": _with_evidence(state, _matches_context(matches)),
        }

    def _search(
        self,
        state: AgentState,
        filters: list[SemanticFilter],
        specs: dict[tuple[str, str], dict],
        tables: list[dict[str, Any]],
    ) -> tuple[list[tuple[SemanticFilter, dict, list[Any]]], dict[str, str]]:
        path_state = state.get("path_state", {})
        connector = resolve_connector_from_tables(tables, state.get("connectors") or [])
        vectors = embed_texts([f.query for f in filters], get_embed_params(), "query")

        matches: list[tuple[SemanticFilter, dict, list[Any]]] = []
        ids_by_placeholder: dict[str, str] = {}
        for number, (found, vector) in enumerate(zip(filters, vectors, strict=True), 1):
            spec = specs[(found.table, found.column)]
            rows = _nearest_rows(connector, spec, found.column, vector)
            candidates = _best_candidates(found.query, rows)
            ids = _verified_ids(state["llm"], found.query, candidates)
            if candidates and len(ids) == len(candidates) and len(rows) == RECALL_K:
                # Every reviewed candidate matched and more were left unreviewed.
                record_thought(path_state, _NODE_NAME, SEMANTIC_TRUNCATED_NOTE)
            matches.append((found, spec, ids))
            ids_by_placeholder[f"__SEMANTIC_{number}__"] = (
                ", ".join(sql_literal(i) for i in ids) or "NULL"
            )
        return matches, ids_by_placeholder
