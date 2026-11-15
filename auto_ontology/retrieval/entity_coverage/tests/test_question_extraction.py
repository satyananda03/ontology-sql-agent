from unittest.mock import MagicMock

import pytest

from auto_ontology.retrieval.entity_coverage.agents import question_extraction
from auto_ontology.retrieval.entity_coverage.agents.question_extraction import (
    QuestionExtractionAgent,
)
from auto_ontology.retrieval.entity_coverage.models import (
    QuestionExtractionLiteModel,
    QuestionExtractionModel,
)


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


_GLOSSARY = [
    {"name": "PR", "description": "pelaku kreatif"},
    {"name": "Korda", "description": "koordinator daerah"},
]


def _run_full(monkeypatch: pytest.MonkeyPatch, answer: object) -> dict:
    monkeypatch.setattr(
        question_extraction,
        "invoke_with_structured_output",
        lambda _llm, _messages, _schema: answer,
    )
    state = {
        "llm": MagicMock(),
        "initial_question": "berapa pr di surabaya?",
        "path_state": {},
        "glossary": list(_GLOSSARY),
    }
    return QuestionExtractionAgent().execute(state)


def _answer(used: list[str]) -> QuestionExtractionModel:
    return QuestionExtractionModel(
        sanitized_question="berapa pelaku kreatif di surabaya?",
        required_entity_name=["pelaku kreatif"],
        subject="pelaku kreatif",
        used_glossary_names=used,
    )


def test_glossary_is_narrowed_to_the_entries_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_full(monkeypatch, _answer(["pr"]))

    assert result["glossary"] == [_GLOSSARY[0]]


def test_an_answer_using_no_entry_empties_the_glossary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The LLM decided none applies, which is a real answer."""
    assert _run_full(monkeypatch, _answer([]))["glossary"] == []


def test_a_failed_call_leaves_the_glossary_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nobody decided the entries were irrelevant, so downstream keeps them all."""
    assert "glossary" not in _run_full(monkeypatch, None)
