"""Table join graph: pure, in-memory logic over semantic FK edges.

:mod:`auto_ontology.dal.attributes` loads the edges and names from the store;
this module only decides what joins to what, so it runs and is tested without a
database, and a caller checking many table pairs loads the edges once.

An edge row is one semantic FK: ``fk_table_id``/``fk_column_id`` referencing
``owner_table_id``/``owner_column_id``, plus ``owner_is_pk``.
"""

from collections import defaultdict, deque
from collections.abc import Callable, Iterable
import logging
from typing import Any

logger = logging.getLogger(__name__)

#: ``next_table_id -> [(next_table_id, source_column_id, target_column_id)]``.
Adjacency = dict[str, list[tuple[str, str, str]]]
#: One hop: the table it enters, and the column pair that joins into it.
Hop = tuple[str, str, str]


def build_adjacency(edge_rows: Iterable[dict[str, Any]]) -> Adjacency:
    """Undirected-where-legitimate table edges, each carrying its join columns.

    The FK -> owner direction is always a real join (that is what a foreign key
    means) and is added both ways only when the owner column is the owner
    table's declared primary key — a genuine identity. Two FK columns that
    merely reference the same non-identity attribute are not joinable to each
    other through it. See ``attributes._find_table_join_hops`` for the full
    rationale.
    """
    adjacency: Adjacency = defaultdict(list)
    for row in edge_rows:
        fk_table_id = row["fk_table_id"]
        owner_table_id = row["owner_table_id"]
        if fk_table_id == owner_table_id:
            continue
        adjacency[fk_table_id].append(
            (owner_table_id, row["fk_column_id"], row["owner_column_id"])
        )
        if row["owner_is_pk"]:
            adjacency[owner_table_id].append(
                (fk_table_id, row["owner_column_id"], row["fk_column_id"])
            )
    for edges in adjacency.values():
        edges.sort()
    return dict(adjacency)


def shortest_path(
    adjacency: Adjacency, anchor_table_id: str, dest_table_id: str, max_hops: int
) -> list[Hop]:
    """Fewest-hop route from anchor to destination table, ``[]`` if none.

    Breadth-first over sorted edges, so the same graph always yields the same
    route. Each hop is ``(entered_table_id, source_column_id, target_column_id)``.
    """
    parents: dict[str, Hop | None] = {anchor_table_id: None}
    frontier: deque[tuple[str, int]] = deque([(anchor_table_id, 0)])
    while frontier:
        table_id, depth = frontier.popleft()
        if depth >= max_hops:
            continue
        for next_table_id, source_col_id, target_col_id in adjacency.get(table_id, []):
            if next_table_id in parents:
                continue
            parents[next_table_id] = (table_id, source_col_id, target_col_id)
            if next_table_id == dest_table_id:
                return _walk_back(parents, dest_table_id)
            frontier.append((next_table_id, depth + 1))
    return []


def _walk_back(parents: dict[str, Hop | None], dest_table_id: str) -> list[Hop]:
    hops: list[Hop] = []
    current = dest_table_id
    while parents[current] is not None:
        previous, source_col_id, target_col_id = parents[current]
        hops.append((current, source_col_id, target_col_id))
        current = previous
    hops.reverse()
    return hops


def bridge_path(
    route: Callable[[str, str], list[Hop]],
    table_a_id: str,
    table_b_id: str,
    allowed_table_ids: set[str] | None = None,
) -> tuple[list[str], list[Hop]]:
    """Tables strictly between *a* and *b* on a route, and that route's hops.

    *route(src, dst)* gives the shortest route from one table to another
    (``[]`` when there is none). It is tried a -> b, then b -> a, because the
    traversal is not symmetric: entering a table from its owner side needs that
    table's own PK to be the shared attribute.

    A direction is skipped when it has no route, when the route is a direct
    join (nothing in between to restore), or when a table in between is not in
    *allowed_table_ids*: the caller restores bridges the relevance filter saw
    and dropped, and never discovers new ones. ``([], [])`` when every
    direction is skipped.
    """
    for src, dst in ((table_a_id, table_b_id), (table_b_id, table_a_id)):
        hops = route(src, dst)
        # Each hop enters the next table; the last one enters dst itself.
        bridge_ids = list(dict.fromkeys(table_id for table_id, _, _ in hops[:-1]))
        if not bridge_ids:
            continue
        if allowed_table_ids is not None and not set(bridge_ids) <= allowed_table_ids:
            logger.info(
                "bridge_path: discarding path %s -> %s — bridge table(s) were never "
                "a candidate, not just restoring a dropped one",
                src,
                dst,
            )
            continue
        return bridge_ids, hops
    return [], []
