# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Match a topic against row text by meaning, using the warehouse's search columns.

Ported from ``classic_sql_agent``. A keyword filter misses a topic worded differently
in the data, so this pre-fetches the matching row ids and hands them to SQL generation
through a placeholder: ids never pass through the LLM, and the generation prompt stays
the original one because the instruction travels separately, as ``semantic_instructions``.

Per topic::

    plan (LLM) → embed → candidates → rerank → verify (LLM) → ids for the generator

Candidates are hybrid when the table has a ``<source>_bm25`` column: the vector arm
(``vector_search``) catches paraphrases, the BM25 arm (``bm25_search``) catches exact
terms and acronyms (SKCK, PKB) that embeddings miss. Both run in parallel and are
merged by Reciprocal Rank Fusion; without the column, the vector arm alone is used.

The classic node kept at most 20 ids, which silently undercounted larger topics. This
one verifies more candidates and reports when even those may not be all of them.
"""

import asyncio
import numbers
from functools import lru_cache
from typing import Any

from auto_ontology.retrieval.text_to_sql.base import record_thought
from auto_ontology.retrieval.text_to_sql.connector_routing import (
    resolve_connector_from_tables,
)
from auto_ontology.retrieval.text_to_sql.state import (
    AgentState,
    get_standalone_question,
)
from sql_agent.core.config import settings
from sql_agent.core.logging import get_logger
from sql_agent.modules.semantic.bm25_search import bm25_column, keyword_rows
from sql_agent.modules.semantic.vector_search import nearest_rows
from sql_agent.schemas import RelevantCandidates, SemanticFilter, SemanticPlan
from sql_agent.services.embedding_service import get_embeddings
from sql_agent.services.llm_service import (
    StructuredChain,
    ainvoke_parsed,
    get_llm,
    structured_chain,
)
from sql_agent.services.prompt_service import PROMPTS_FILE
from sql_agent.services.rerank_service import get_reranker

logger = get_logger(__name__)

_NODE_NAME = "semantic_rows"
# Recorded when more rows may match than were reviewed; the service reports it.
SEMANTIC_TRUNCATED_NOTE = "semantic_search_truncated"
_VECTOR_SUFFIX = "_vector"
# Candidates per arm, and the most the fused list hands the reranker.
RECALL_K = 100
VERIFY_K = 50
RRF_K = 60  # the usual Reciprocal Rank Fusion constant
EMBED_TIMEOUT_S = 20.0
RERANK_TIMEOUT_S = 30.0
# Ceiling on one planner or verifier reply; they run to a few hundred tokens.
SEMANTIC_MAX_TOKENS = 5000
# Topics are searched in parallel. Each takes two pooled connections (one per
# arm), and the connector pool holds four.
SEARCH_WORKERS = 2


@lru_cache(maxsize=2)
def _chain(prompt_name: str, schema: type) -> StructuredChain:
    llm = get_llm(
        settings.llm_model,
        max_tokens=SEMANTIC_MAX_TOKENS,
        timeout=settings.sql_agent_llm_timeout_s,
    )
    return structured_chain(llm, PROMPTS_FILE, prompt_name, schema)


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


def rrf(*arms: list[dict]) -> list[dict]:
    """Rows of every arm, best first by Reciprocal Rank Fusion on ``id``.

    A row ranked well by both arms rises above one ranked first by only one; ties
    keep the order of the first arm.
    """
    scores: dict[Any, float] = {}
    rows: dict[Any, dict] = {}
    for arm in arms:
        for rank, row in enumerate(arm, 1):
            scores[row["id"]] = scores.get(row["id"], 0.0) + 1 / (RRF_K + rank)
            rows.setdefault(row["id"], row)
    return [rows[i] for i in sorted(scores, key=scores.__getitem__, reverse=True)]


def _bm25_rows(connector: Any, spec: dict, query: str) -> list[dict]:
    """The BM25 arm, or no rows when the table has none or it fails.

    Keywords only add recall to the vector arm, so a missing pg_search index must
    not take the topic's search down with it.
    """
    try:
        column = bm25_column(connector, spec)
        return keyword_rows(connector, spec, column, query, RECALL_K) if column else []
    except Exception:  # noqa: BLE001 — the vector arm still answers
        logger.warning("BM25 search failed; using vector only", exc_info=True)
        return []


async def _candidates(
    connector: Any, spec: dict, found: SemanticFilter, vector: list[float]
) -> tuple[list[dict], bool]:
    """Fused candidates for one topic, and whether either arm hit ``RECALL_K``."""
    vector_rows, bm25_rows = await asyncio.gather(
        asyncio.to_thread(
            nearest_rows, connector, spec, found.column, vector, RECALL_K
        ),
        asyncio.to_thread(_bm25_rows, connector, spec, found.query),
    )
    logger.info(
        f"[RETRIEVAL] {found.table}.{spec['source']}: "
        f"{len(vector_rows)} vector + {len(bm25_rows)} bm25 candidate(s)"
    )
    full = RECALL_K in (len(vector_rows), len(bm25_rows))
    return rrf(vector_rows, bm25_rows)[:RECALL_K], full


async def _best_candidates(query: str, rows: list[dict]) -> list[dict]:
    """Rerank when a reranker is configured, otherwise keep the fused order."""
    if len(rows) <= 1:
        return rows
    try:
        # One attempt: ranking is an optimization, so a slow endpoint must not
        # eat the question's time budget on retries.
        rerank = get_reranker(timeout=RERANK_TIMEOUT_S, max_retries=1)
        ranked = await rerank(
            query, [str(row.get("snippet") or "") for row in rows], top_n=VERIFY_K
        )
        ranked.sort(key=lambda hit: hit["relevance_score"], reverse=True)
        return [rows[hit["index"]] for hit in ranked][:VERIFY_K]
    except Exception:  # noqa: BLE001 — ranking is an optimization, not a requirement
        logger.warning("Rerank failed; keeping fused order", exc_info=True)
        return rows[:VERIFY_K]


async def _verified_ids(topic: str, candidates: list[dict]) -> list[Any]:
    if not candidates:
        return []
    listing = "\n".join(
        f"{number}. {' '.join(str(row.get('snippet') or '').split())}"
        for number, row in enumerate(candidates, 1)
    )
    result = await ainvoke_parsed(
        _chain("semantic_verifier", RelevantCandidates),
        {"topic": topic, "candidates": listing},
    )
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


async def _search(
    state: AgentState,
    filters: list[SemanticFilter],
    specs: dict[tuple[str, str], dict],
    tables: list[dict[str, Any]],
) -> tuple[list[tuple[SemanticFilter, dict, list[Any]]], dict[str, str]]:
    path_state = state.get("path_state", {})
    connector = resolve_connector_from_tables(tables, state.get("connectors") or [])
    # Interactive limits (one retry): the defaults are sized for batch work.
    vectors = await get_embeddings(
        timeout=EMBED_TIMEOUT_S, max_retries=2
    ).aembed_documents([f.query.strip() for f in filters])
    slots = asyncio.Semaphore(SEARCH_WORKERS)

    async def search_one(
        found: SemanticFilter, vector: list[float]
    ) -> tuple[bool, list[dict], list[Any]]:
        spec = specs[(found.table, found.column)]
        async with slots:
            rows, full = await _candidates(connector, spec, found, vector)
            candidates = await _best_candidates(found.query, rows)
            return full, candidates, await _verified_ids(found.query, candidates)

    # Topics are independent: search, rerank and verify them in parallel.
    results = await asyncio.gather(
        *(search_one(found, vector) for found, vector in zip(filters, vectors))
    )

    matches: list[tuple[SemanticFilter, dict, list[Any]]] = []
    ids_by_placeholder: dict[str, str] = {}
    for number, (found, (full, candidates, ids)) in enumerate(
        zip(filters, results, strict=True), 1
    ):
        spec = specs[(found.table, found.column)]
        if candidates and len(ids) == len(candidates) and full:
            # Every reviewed candidate matched and more were left unreviewed.
            record_thought(path_state, _NODE_NAME, SEMANTIC_TRUNCATED_NOTE)
        matches.append((found, spec, ids))
        ids_by_placeholder[f"__SEMANTIC_{number}__"] = (
            ", ".join(sql_literal(i) for i in ids) or "NULL"
        )
    return matches, ids_by_placeholder


async def _semantic_rows(state: AgentState) -> dict[str, Any]:
    path_state = state.get("path_state", {})
    path_state["semantic_ids"] = {}
    tables = path_state.get("relevant_tables") or []
    specs = searchable_columns(tables)
    if not specs:
        return {"path_state": path_state}

    columns = "\n".join(
        f"- {table}.{column}: {spec['description'] or spec['source']}"
        for (table, column), spec in specs.items()
    )
    plan = await ainvoke_parsed(
        _chain("semantic_planner", SemanticPlan),
        {"question": get_standalone_question(state), "columns": columns},
    )
    filters = [
        found
        for found in (plan.filters if plan else [])
        if (found.table, found.column) in specs and found.query.strip()
    ]
    if not filters:
        return {"path_state": path_state}

    try:
        matches, ids_by_placeholder = await _search(state, filters, specs, tables)
    except Exception:  # noqa: BLE001 — degrade to keywords rather than fail the run
        logger.warning("Semantic search failed", exc_info=True)
        return {
            "path_state": path_state,
            "semantic_instructions": _fallback_context(filters, specs),
        }
    path_state["semantic_ids"] = ids_by_placeholder
    return {
        "path_state": path_state,
        "semantic_instructions": _matches_context(matches),
    }


async def semantic_rows(state: AgentState) -> dict[str, Any]:
    """Pre-fetch row ids for topic constraints in the question.

    A failure here leaves the question without topic matches instead of ending
    the run: the generator then filters with keywords, as it would without this.
    """
    try:
        return await _semantic_rows(state)
    except Exception:  # noqa: BLE001 — semantic search is an optimization
        logger.error("Semantic rows failed", exc_info=True)
        return {"path_state": state.get("path_state", {})}
