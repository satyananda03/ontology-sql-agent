import pytest

from auto_ontology.retrieval.text_to_sql.anchor import select_anchor

# Best distance first, as candidate retrieval hands them over.
HITS = [
    {"id": "region", "query_entities": ["region"]},
    {"id": "budget", "query_entities": ["Festival"]},
    {"id": "level", "query_entities": ["festival level"]},
]
CONTEXTS = {
    "budget": {"term_ids": ["t-finance"]},
    "level": {"term_ids": ["t-festival"]},
    "region": {"term_ids": ["t-geo"]},
}


@pytest.mark.parametrize(
    ("hits", "contexts", "subject", "term_id", "expected"),
    [
        pytest.param(
            HITS,
            CONTEXTS,
            "festival ",
            "t-festival",
            ("budget", "subject_entity"),
            id="subject phrase beats subject term and better scores, casefolded",
        ),
        pytest.param(
            HITS,
            CONTEXTS,
            "organizer",
            "t-festival",
            ("level", "subject_term"),
            id="subject term when no hit came from the subject phrase",
        ),
        pytest.param(
            HITS,
            CONTEXTS,
            "organizer",
            "t-missing",
            ("region", "top_hit"),
            id="best score when no subject signal matches",
        ),
        pytest.param(
            HITS,
            CONTEXTS,
            "",
            None,
            ("region", "top_hit"),
            id="without subject signals it is plain top-hit",
        ),
        pytest.param(
            HITS,
            {"level": {"term_ids": []}},
            "region",
            None,
            ("level", "top_hit"),
            id="hits without catalog context are skipped",
        ),
        pytest.param(
            [],
            {"orphan": {"term_ids": []}},
            "x",
            None,
            ("orphan", "first_context"),
            id="no usable hit falls back to the first context",
        ),
        pytest.param([], {}, "x", None, (None, "none"), id="nothing to choose"),
    ],
)
def test_select_anchor(hits, contexts, subject, term_id, expected) -> None:
    assert select_anchor(hits, contexts, subject, term_id) == expected
