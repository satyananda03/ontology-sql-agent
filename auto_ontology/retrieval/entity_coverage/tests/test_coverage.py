from auto_ontology.retrieval.entity_coverage.agents.coverage import (
    _filter_by_distance,
    _rank_candidates,
)


def test_a_zero_distance_hit_is_kept_and_ranked_first() -> None:
    # Cosine distance 0.0 is the best match, not a missing score.
    hits = [{"id": "near", "score": 0.3}, {"id": "exact", "score": 0.0}]

    kept = _filter_by_distance(hits, max_distance=0.5)

    assert [h["id"] for h in _rank_candidates(kept)] == ["exact", "near"]


def test_a_hit_without_a_score_is_dropped() -> None:
    assert _filter_by_distance([{"id": "unscored"}], max_distance=0.5) == []
