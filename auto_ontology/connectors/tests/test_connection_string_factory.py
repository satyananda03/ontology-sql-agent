# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from urllib.parse import unquote, urlparse

import pytest

from auto_ontology.connectors.connection_string_factory import build_connection_string


def _postgres(**overrides: object) -> dict[str, object]:
    connection = {
        "type": "postgres",
        "host": "db.internal",
        "port": "5433",
        "user": "svc_user",
        "password": "secret",
        "database": "warehouse",
    }
    connection.update(overrides)
    return connection


def test_builds_a_postgresql_url() -> None:
    assert (
        build_connection_string(_postgres())
        == "postgresql://svc_user:secret@db.internal:5433/warehouse"
    )


def test_reserved_characters_in_credentials_are_escaped() -> None:
    """A ``/`` or ``@`` in the password must not be read as URL structure."""
    parsed = urlparse(build_connection_string(_postgres(password="p@ss/word")))

    assert parsed.hostname == "db.internal"
    assert unquote(parsed.password or "") == "p@ss/word"


def test_port_defaults_when_blank() -> None:
    assert urlparse(build_connection_string(_postgres(port=" "))).port == 5432


@pytest.mark.parametrize("conn_type", ["postgresql", "Postgres"])
def test_type_aliases_are_accepted(conn_type: str) -> None:
    assert build_connection_string(_postgres(type=conn_type)).startswith(
        "postgresql://"
    )


@pytest.mark.parametrize("field", ["host", "user", "password", "database"])
def test_required_fields_are_enforced(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        build_connection_string(_postgres(**{field: ""}))


def test_other_engines_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported connection type"):
        build_connection_string(_postgres(type="snowflake"))
