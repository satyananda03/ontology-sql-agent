from unittest.mock import MagicMock

import pytest

from auto_ontology.retrieval.entity_coverage.agents import question_extraction
from auto_ontology.retrieval.entity_coverage.agents.question_extraction import (
    QuestionExtractionAgent,
)
from auto_ontology.retrieval.entity_coverage.models import QuestionExtractionLiteModel


def test_agent_fills_path_state_without_changing_original_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        question_extraction,
        "invoke_with_structured_output",
        lambda _llm, _messages, _schema: QuestionExtractionLiteModel(
            sanitized_question="Show loyalty points earned by customers",
            required_entity_name=["loyalty points", "customer"],
        ),
    )
    state = {
        "llm": MagicMock(),
        "initial_question": "Show points earned by customers",
        "path_state": {},
        "glossary": [],
    }

    result = QuestionExtractionAgent(include_subject=False).execute(state)

    assert state["initial_question"] == "Show points earned by customers"
    assert result["path_state"]["normalized_question"] == (
        "Show loyalty points earned by customers"
    )
    assert result["path_state"]["entities"] == ["loyalty points", "customer"]
