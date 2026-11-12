# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""auto_ontology's retrieval agents, run in order for one standalone question.

Entity extraction, vector search over Terms and columns, then graph search for
join paths. Only the state those three agents read is built: the caller already
rewrote the question and only asks for data, so intent classification, chat
history and the SQL-generation keys of the full agent are not needed.
"""

import os
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
from auto_ontology.retrieval.text_to_sql.state import (
    AgentState,
    get_standalone_question,
)
from sql_agent.utils import llm_timeout_s, timed

# Ceiling on one retrieval reply (entities, candidate and table filters). They
# run to a few hundred tokens; ingestion keeps the client's larger default.
RETRIEVAL_MAX_TOKENS = 5000


class CallerQuestionExtractionAgent(QuestionExtractionAgent):
    """Extract entities, but keep the question exactly as the caller wrote it."""

    def execute(self, state: AgentState) -> dict[str, Any]:
        result = super().execute(state)
        result["path_state"]["normalized_question"] = get_standalone_question(state)
        return result


def rerank_pool() -> int | None:
    """Vector hits each catalog search hands the reranker; ``0`` turns it off."""
    return int(os.environ.get("SQL_AGENT_RERANK_POOL") or 10) or None


RETRIEVAL_STEPS = (
    timed("question_extraction", agent_wrapper(CallerQuestionExtractionAgent())),
    timed(
        "candidate_retrieval",
        agent_wrapper(CandidateRetrievalAgent(rerank_pool=rerank_pool())),
    ),
    timed(
        "candidate_preparation",
        agent_wrapper(CandidatePreparationAgent(rerank_pool=rerank_pool())),
    ),
)


@lru_cache(maxsize=1)
def _llm() -> Any:
    from auto_ontology.utils.llm_invoke import get_non_reasoning_llm_client

    return get_non_reasoning_llm_client(
        max_tokens=RETRIEVAL_MAX_TOKENS, timeout=llm_timeout_s()
    )


def build_state(question: str) -> dict[str, Any]:
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
    # The one source database; auto_ontology's agents still read it as target_db.
    path_state: dict[str, Any] = {
        "processing_question": question,
        "target_db": connectors[0].database_name,
    }
    glossary = fetch_acronyms()
    return {
        "llm": _llm(),
        "initial_question": question,
        "enriched_question": "",
        "value_anchors": [],
        "connectors": connectors,
        "data_retriever": get_data_objects_retriever(),
        "semantic_retriever": get_semantic_objects_retriever(),
        "glossary": list(glossary),
        "domain_rules": list(glossary),
        "path_state": path_state,
    }


def warm_up() -> None:
    """Build the state once and run one throwaway search per vector store.

    Pools and vector stores connect on first use, not when they are built, so
    without a real query the first question pays for every connection.
    """
    state = build_state("warm up")
    # ponytail: opens one connection per pool; the parallel searches of the
    # first real question open the rest (measured ~3s, once). Warm up with
    # parallel searches if that first question matters.
    for retriever in (state["semantic_retriever"], state["data_retriever"]):
        retriever.query("warm up", top_k=1)


def merge(state: dict[str, Any], output: dict[str, Any] | None) -> None:
    """Fold one step's output into *state*; ``path_state`` merges key by key."""
    if not output:
        return
    state.setdefault("path_state", {}).update(output.get("path_state") or {})
    state.update({key: value for key, value in output.items() if key != "path_state"})


def retrieve(question: str) -> dict[str, Any]:
    """Run the retrieval steps for *question* and return the agent state."""
    state = build_state(question)
    for step in RETRIEVAL_STEPS:
        merge(state, step(state))
    return state
