"""The join graph's rules, on hand-written edges: no database needed."""

from auto_ontology.dal import join_graph as g


def _edge(fk: str, owner: str, owner_is_pk: bool = True) -> dict:
    """``fk`` and ``owner`` as ``table.column``; column ids are the same strings."""
    return {
        "fk_table_id": fk.split(".")[0],
        "fk_column_id": fk,
        "owner_table_id": owner.split(".")[0],
        "owner_column_id": owner,
        "owner_is_pk": owner_is_pk,
    }


# orders -> customers -> addresses, each FK into the owner's primary key.
CHAIN = [
    _edge("orders.customer_id", "customers.id"),
    _edge("customers.address_id", "addresses.id"),
]


def _route(edges: list[dict], max_hops: int = 7):
    adjacency = g.build_adjacency(edges)
    return lambda src, dst: g.shortest_path(adjacency, src, dst, max_hops)


def test_a_pk_owner_joins_both_ways_and_any_other_owner_one_way() -> None:
    adjacency = g.build_adjacency(
        [_edge("a.x", "b.id"), _edge("c.y", "d.code", owner_is_pk=False)]
    )
    assert adjacency["a"] == [("b", "a.x", "b.id")]
    assert adjacency["b"] == [("a", "b.id", "a.x")]
    assert adjacency["c"] == [("d", "c.y", "d.code")]
    assert "d" not in adjacency


def test_a_self_reference_is_not_an_edge() -> None:
    assert g.build_adjacency([_edge("t.parent_id", "t.id")]) == {}


def test_shortest_path_names_the_table_each_hop_enters() -> None:
    assert _route(CHAIN)("orders", "addresses") == [
        ("customers", "orders.customer_id", "customers.id"),
        ("addresses", "customers.address_id", "addresses.id"),
    ]


def test_shortest_path_stops_at_max_hops() -> None:
    assert _route(CHAIN, max_hops=1)("orders", "addresses") == []


def test_the_table_in_between_is_the_bridge() -> None:
    bridge_ids, hops = g.bridge_path(_route(CHAIN), "orders", "addresses")
    assert bridge_ids == ["customers"]
    assert [table for table, _, _ in hops] == ["customers", "addresses"]


def test_a_direct_join_is_not_a_bridge() -> None:
    assert g.bridge_path(_route(CHAIN), "orders", "customers") == ([], [])


def test_the_reverse_direction_is_tried_when_the_first_has_no_route() -> None:
    one_way = [
        _edge("orders.customer_id", "customers.code", owner_is_pk=False),
        _edge("customers.address_id", "addresses.code", owner_is_pk=False),
    ]
    bridge_ids, _ = g.bridge_path(_route(one_way), "addresses", "orders")
    assert bridge_ids == ["customers"]


def test_a_bridge_that_was_never_a_candidate_is_discarded() -> None:
    route = _route(CHAIN)
    assert g.bridge_path(route, "orders", "addresses", {"orders", "addresses"}) == (
        [],
        [],
    )
    bridge_ids, _ = g.bridge_path(route, "orders", "addresses", {"customers"})
    assert bridge_ids == ["customers"]
