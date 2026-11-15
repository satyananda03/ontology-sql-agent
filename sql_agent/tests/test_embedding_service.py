# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
from types import SimpleNamespace

import pytest

from sql_agent.services.embedding_service import embed_by_index, embed_by_index_sync


def _response(*indexes: int) -> SimpleNamespace:
    return SimpleNamespace(
        data=[SimpleNamespace(index=i, embedding=[float(i)]) for i in indexes]
    )


def test_vectors_follow_their_index_not_their_position() -> None:
    # Two texts per request; the endpoint answers each one in reverse order.
    calls: list[list[str]] = []

    def create(input: list[str]) -> SimpleNamespace:
        calls.append(input)
        return _response(*reversed(range(len(input))))

    assert embed_by_index_sync(create, ["a", "b", "c"], 2) == [[0.0], [1.0], [0.0]]
    assert calls == [["a", "b"], ["c"]]


@pytest.mark.parametrize("indexes", [(0,), (0, 0), (0, 2)])
def test_a_missing_or_duplicate_vector_is_rejected(indexes: tuple[int, ...]) -> None:
    async def create(input: list[str]) -> SimpleNamespace:
        return _response(*indexes)

    with pytest.raises(RuntimeError, match="for 2 input"):
        asyncio.run(embed_by_index(create, ["a", "b"], 2))
