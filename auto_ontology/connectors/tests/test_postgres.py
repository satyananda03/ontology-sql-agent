# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Catalog introspection tests for the Postgres connector.

Runs against the Pagila fixture, which is the only fixture that has a
partitioned table and a materialized view — the two relation kinds this
connector used to drop silently. Skipped when no fixture database is reachable.

Set up with::

    docker compose up -d postgres
    uv run --no-sync python -m dev_tools.fixtures.seed_fixtures
"""

from __future__ import annotations

import os
import secrets

import pytest

from auto_ontology.catalog.constants import TableTypes
from auto_ontology.connectors.registry import create_connector


def _pagila_url(user: str, password: str) -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/pagila"


@pytest.fixture(scope="module")
def pagila():
    if not os.environ.get("POSTGRES_USER"):
        pytest.skip("POSTGRES_* not set; run dev_tools.fixtures.seed_fixtures first")
    try:
        connector = create_connector(
            _pagila_url(os.environ["POSTGRES_USER"], os.environ["POSTGRES_PASSWORD"])
        )
        connector.get_tables()
    except Exception as exc:  # noqa: BLE001 — any failure means "no fixture DB"
        pytest.skip(f"pagila not reachable: {exc}")
    yield connector
    connector.close()


@pytest.fixture(scope="module")
def public_tables(pagila):
    tables = pagila.get_tables()
    return tables[tables.table_schema == "public"]


def test_partitioned_parent_is_catalogued(public_tables) -> None:
    """``payment`` is partitioned. It used to vanish entirely.

    ``relispartition = false`` correctly hid the children, but ``relkind`` did
    not allow ``'p'``, so the parent was dropped too and an entire queryable
    table was missing from the catalog.
    """
    payment = public_tables[public_tables.table_name == "payment"]
    assert len(payment) == 1, "partitioned parent missing from the catalog"
    assert payment.table_type.iloc[0] == TableTypes.BASE_TABLE


def test_partition_children_are_not_catalogued(public_tables) -> None:
    """Children are an implementation detail; listing both double-counts rows."""
    children = public_tables[public_tables.table_name.str.startswith("payment_p")]
    assert children.empty, f"partition children leaked: {list(children.table_name)}"


def test_materialized_view_is_catalogued(public_tables) -> None:
    """``rental_by_category`` is a matview.

    Matviews are absent from ``information_schema.tables``, so driving the query
    from there meant ``TableTypes.MATERIALIZED_VIEW`` could never be produced —
    the ``relkind = 'm'`` branch was unreachable.
    """
    matview = public_tables[public_tables.table_name == "rental_by_category"]
    assert len(matview) == 1, "materialized view missing from the catalog"
    assert matview.table_type.iloc[0] == TableTypes.MATERIALIZED_VIEW


def test_all_three_table_types_are_produced(public_tables) -> None:
    """Every ``TableTypes`` value is reachable, not just ``base table``."""
    assert set(public_tables.table_type) == {
        TableTypes.BASE_TABLE,
        TableTypes.VIEW,
        TableTypes.MATERIALIZED_VIEW,
    }


def test_columns_reach_every_catalogued_relation(pagila, public_tables) -> None:
    """A relation with no columns is useless downstream.

    Matview columns are missing from ``information_schema.columns`` too, so this
    would have been empty for ``rental_by_category`` even once the table itself
    was listed.
    """
    columns = pagila.get_columns()
    public_columns = columns[columns.table_schema == "public"]
    with_columns = set(public_columns.table_name)
    missing = set(public_tables.table_name) - with_columns
    assert not missing, f"catalogued relations with no columns: {sorted(missing)}"


def test_declared_types_are_reported_not_placeholders(pagila) -> None:
    """Enums, arrays and domains report their real type.

    ``information_schema.columns.data_type`` collapses these to
    ``USER-DEFINED`` and ``ARRAY``, which tells a SQL-generating model nothing.
    """
    columns = pagila.get_columns()
    film = columns[
        (columns.table_schema == "public") & (columns.table_name == "film")
    ].set_index("column_name")

    assert film.loc["rating", "data_type"] == "mpaa_rating"
    assert film.loc["special_features", "data_type"] == "text[]"
    assert "USER-DEFINED" not in set(columns.data_type)
    assert "ARRAY" not in set(columns.data_type)


def test_system_schemas_are_excluded(pagila) -> None:
    schemas = set(pagila.get_tables().table_schema)
    assert schemas == {"public", "analytics"}, schemas


def test_nullability_is_a_real_boolean(pagila) -> None:
    """Not the ``'YES'``/``'NO'`` text ``information_schema`` reports.

    Both spellings are truthy, so leaking them makes every column read as
    nullable — the bug this connector's ``NOT a.attnotnull`` avoids by never
    producing a string in the first place.
    """
    columns = pagila.get_columns()
    assert columns.is_nullable.dtype == bool
    assert set(columns.is_nullable) <= {True, False}

    film = columns[
        (columns.table_schema == "public") & (columns.table_name == "film")
    ].set_index("column_name")
    assert bool(film.loc["film_id", "is_nullable"]) is False, "film_id is NOT NULL"
    assert bool(film.loc["description", "is_nullable"]) is True

    # The real assertion: a mix, not a column of all-True. The bug's signature
    # was every column agreeing.
    assert 0 < int(columns.is_nullable.sum()) < len(columns)


@pytest.fixture(scope="module")
def select_only_pagila(pagila):
    """Pagila through a role that owns nothing and holds only ``SELECT``."""
    role = "auto_ontology_test_select_only"
    password = secrets.token_hex(16)
    try:
        pagila.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{password}'")
    except Exception as exc:  # noqa: BLE001 — any failure means "cannot create roles"
        pytest.skip(f"cannot create a test role: {exc}")
    connector = None
    try:
        pagila.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        pagila.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}")
        connector = create_connector(_pagila_url(role, password))
        yield connector
    finally:
        if connector is not None:
            connector.close()
        pagila.execute(f"DROP OWNED BY {role}")
        pagila.execute(f"DROP ROLE {role}")


KEY_CASES_SCHEMA = "auto_ontology_test_keys"


@pytest.fixture(scope="module")
def key_cases(pagila):
    """Constraint shapes Pagila does not declare, in a schema of their own."""
    schema = KEY_CASES_SCHEMA
    pagila.execute(f"CREATE SCHEMA {schema}")
    try:
        pagila.execute(
            f"CREATE TABLE {schema}.parent (a int, b int, PRIMARY KEY (a, b))"
        )
        pagila.execute(
            f"CREATE TABLE {schema}.child (x int, y int, "
            f"FOREIGN KEY (y, x) REFERENCES {schema}.parent (b, a))"
        )
        pagila.execute(
            f"CREATE TABLE {schema}.part (id int PRIMARY KEY) PARTITION BY RANGE (id)"
        )
        for number in (1, 2):
            pagila.execute(
                f"CREATE TABLE {schema}.part_{number} PARTITION OF {schema}.part "
                f"FOR VALUES FROM ({number}) TO ({number + 1})"
            )
        pagila.execute(
            f"CREATE TABLE {schema}.to_part (part_id int REFERENCES {schema}.part (id))"
        )
        yield pagila
    finally:
        pagila.execute(f"DROP SCHEMA {schema} CASCADE")


def _key_columns(pks, table: str) -> list[str]:
    rows = pks[(pks.table_schema == "public") & (pks.table_name == table)]
    return rows.sort_values("ordinal_position").column_name.tolist()


def _references(fks, table: str, schema: str = "public") -> set[tuple[str, str, str]]:
    rows = fks[(fks.table_schema == schema) & (fks.table_name == table)]
    return set(
        zip(
            rows.column_name, rows.referenced_table, rows.referenced_column, strict=True
        )
    )


def test_primary_keys_keep_their_column_order(pagila) -> None:
    """``film_actor`` declares a composite key; its order must survive."""
    pks = pagila.get_pks()
    assert _key_columns(pks, "film") == ["film_id"]
    assert _key_columns(pks, "film_actor") == ["actor_id", "film_id"]


def test_foreign_keys_name_their_target(pagila) -> None:
    assert _references(pagila.get_fks(), "film_actor") == {
        ("actor_id", "actor", "actor_id"),
        ("film_id", "film", "film_id"),
    }


def test_database_comments_become_descriptions(key_cases) -> None:
    """A comment already written in the database should not be re-guessed by an LLM."""
    schema = KEY_CASES_SCHEMA
    key_cases.execute(f"COMMENT ON TABLE {schema}.parent IS 'Parent rows'")
    key_cases.execute(f"COMMENT ON COLUMN {schema}.parent.a IS 'First key part'")

    tables = key_cases.get_tables()
    parent = tables[(tables.table_schema == schema) & (tables.table_name == "parent")]
    assert parent.description.iloc[0] == "Parent rows"

    columns = key_cases.get_columns()
    column = columns[
        (columns.table_schema == schema)
        & (columns.table_name == "parent")
        & (columns.column_name == "a")
    ]
    assert column.description.iloc[0] == "First key part"


def test_composite_foreign_key_pairs_columns_by_position(key_cases) -> None:
    """Columns declared in a different order than the target's must stay paired."""
    assert _references(key_cases.get_fks(), "child", schema=KEY_CASES_SCHEMA) == {
        ("x", "parent", "a"),
        ("y", "parent", "b"),
    }


def test_foreign_key_to_partitioned_table_is_listed_once(key_cases) -> None:
    """Postgres derives one extra constraint per partition of the target."""
    assert _references(key_cases.get_fks(), "to_part", schema=KEY_CASES_SCHEMA) == {
        ("part_id", "part", "id"),
    }


def test_select_only_role_sees_the_same_keys_as_the_owner(
    pagila, select_only_pagila
) -> None:
    """A read-only role used to see none, leaving the catalog with no keys at all.

    ``information_schema`` filters constraints by privilege and ownership, so
    every table lost its primary key and every declared foreign key vanished.
    """
    pk_columns = ["table_schema", "table_name", "column_name", "ordinal_position"]
    fk_columns = [
        "table_schema",
        "table_name",
        "column_name",
        "referenced_schema",
        "referenced_table",
        "referenced_column",
    ]

    def public_rows(frame, columns):
        rows = frame[frame.table_schema == "public"][columns]
        return rows.sort_values(columns).reset_index(drop=True)

    owner_pks = public_rows(pagila.get_pks(), pk_columns)
    owner_fks = public_rows(pagila.get_fks(), fk_columns)
    assert not owner_pks.empty and not owner_fks.empty
    assert owner_pks.equals(public_rows(select_only_pagila.get_pks(), pk_columns))
    assert owner_fks.equals(public_rows(select_only_pagila.get_fks(), fk_columns))
