# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""auto_ontology's retrieval agents, run in order for one standalone question.

Entity extraction, vector search over Terms and columns, then graph search for
join paths. Only the state those three agents read is built: the caller already
rewrote the question and only asks for data, so intent classification, chat
history and the SQL-generation keys of the full agent are not needed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from auto_ontology.retrieval.entity_coverage.agents.question_extraction import (
    QuestionExtractionAgent,
)
from auto_ontology.retrieval.text_to_sql.agents.candidates_preparation import (
    CandidatePreparationAgent,
)
from auto_ontology.retrieval.text_to_sql.agents.candidates_retrieval import (
    CandidateRetrievalAgent,
)
from auto_ontology.retrieval.text_to_sql.base import agent_wrapper
from auto_ontology.retrieval.text_to_sql.connector_routing import (
    resolve_target_database_name,
)
from auto_ontology.retrieval.text_to_sql.state import (
    AgentState,
    get_standalone_question,
)


class CallerQuestionExtractionAgent(QuestionExtractionAgent):
    """Extract entities, but keep the question exactly as the caller wrote it."""

    def execute(self, state: AgentState) -> dict[str, Any]:
        result = super().execute(state)
        result["path_state"]["normalized_question"] = get_standalone_question(state)
        return result


class TopHitCandidatePreparationAgent(CandidatePreparationAgent):
    """Start join paths from the best retrieval hit rather than asking an LLM."""

    def _identify_anchor(
        self,
        state: AgentState,
        question: str,
        contexts: dict[str, dict],
    ) -> tuple[str | None, str]:
        hits = state.get("path_state", {}).get("retrieved_column_attributes") or []
        for hit in hits:
            attribute_id = str(hit.get("id") or "")
            if attribute_id in contexts:
                return attribute_id, ""
        return next(iter(contexts), None), ""


RETRIEVAL_STEPS = (
    agent_wrapper(CallerQuestionExtractionAgent()),
    agent_wrapper(CandidateRetrievalAgent()),
    agent_wrapper(TopHitCandidatePreparationAgent()),
)


@lru_cache(maxsize=1)
def _llm() -> Any:
    from auto_ontology.utils.llm_invoke import get_non_reasoning_llm_client

    return get_non_reasoning_llm_client()


def build_state(
    question: str, *, target_db: str | None = None, evidence: str = ""
) -> dict[str, Any]:
    """The agent state the retrieval steps read, for one question."""
    # Imported here: these open connection pools at import time, which must not
    # happen just because the server registered the route.
    from auto_ontology.connectors import get_connectors
    from auto_ontology.server.settings_dal import fetch_acronyms
    from auto_ontology.utils import (
        get_data_objects_retriever,
        get_semantic_objects_retriever,
    )

    connectors = get_connectors()
    if not connectors:
        raise ValueError("No database connection is configured.")
    path_state: dict[str, Any] = {"processing_question": question}
    if target_db:
        path_state["target_db"] = resolve_target_database_name(target_db, connectors)
    elif len(connectors) == 1 and getattr(connectors[0], "database_name", None):
        path_state["target_db"] = connectors[0].database_name
    glossary = fetch_acronyms()
    return {
        "llm": _llm(),
        "initial_question": question,
        "evidence": evidence,
        "enriched_question": "",
        "value_anchors": [],
        "connectors": connectors,
        "data_retriever": get_data_objects_retriever(),
        "semantic_retriever": get_semantic_objects_retriever(),
        "glossary": list(glossary),
        "domain_rules": list(glossary),
        "path_state": path_state,
    }


def merge(state: dict[str, Any], output: dict[str, Any] | None) -> None:
    """Fold one step's output into *state*; ``path_state`` merges key by key."""
    if not output:
        return
    state.setdefault("path_state", {}).update(output.get("path_state") or {})
    state.update({key: value for key, value in output.items() if key != "path_state"})


def retrieve(
    question: str, *, target_db: str | None = None, evidence: str = ""
) -> dict[str, Any]:
    """Run the retrieval steps for *question* and return the agent state."""
    state = build_state(question, target_db=target_db, evidence=evidence)
    for step in RETRIEVAL_STEPS:
        merge(state, step(state))
    return state
