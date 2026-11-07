# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import patch

from auto_ontology.server.connections import service
from auto_ontology.server.connections.router import _serialize_connection


def _postgres_connection(**extra: object) -> dict[str, object]:
    return {
        "type": "postgres",
        "host": "db.internal",
        "port": "5432",
        "user": "user",
        "password": "secret",
        "database": "database",
        **extra,
    }


class _StubConnector:
    def __init__(self) -> None:
        self.pinged = False
        self.closed = False

    def ping(self) -> None:
        self.pinged = True

    def close(self) -> None:
        self.closed = True


def test_create_connection_persists_connection_without_vault() -> None:
    connection = _postgres_connection(table_deny_regex="^tmp_")

    with (
        patch.object(service, "_database_already_connected", return_value=False),
        patch.object(service, "is_vault_configured", return_value=False),
        patch.object(service, "insert_connection") as insert_connection,
        patch.object(service, "invalidate_connectors_cache"),
        patch.object(service, "trigger_ingest") as trigger_ingest,
    ):
        service.create_connection(connection=connection)

    stored = json.loads(insert_connection.call_args.kwargs["connection"])
    assert stored["password"] == "secret"
    assert stored["table_deny_regex"] == "^tmp_"
    trigger_ingest.assert_called_once_with(connection)


def test_public_connection_payload_redacts_credentials() -> None:
    serialized = _serialize_connection(
        _postgres_connection(password_env="POSTGRES_PASSWORD")
    )

    assert serialized["database_name"] == "database"
    assert "password" not in serialized["connection"]
    assert "password_env" not in serialized["connection"]
    assert "secret" not in json.dumps(serialized)


def test_test_connection_pings_and_closes() -> None:
    connector = _StubConnector()

    with (
        patch.object(service, "_database_already_connected", return_value=False),
        patch.object(service, "create_connector", return_value=connector),
    ):
        schemas = service.test_connection(_postgres_connection())

    assert schemas == []
    assert connector.pinged and connector.closed


def test_test_connection_allows_the_connection_an_edit_replaces() -> None:
    """Without `replacing`, re-testing an existing connection fails the duplicate
    check — an edit could never be validated before saving."""
    connector = _StubConnector()

    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "create_connector", return_value=connector),
    ):
        service.test_connection(_postgres_connection(password=""), replacing="database")

    assert connector.pinged


def test_test_connection_rejects_renaming_the_database_it_replaces() -> None:
    with patch.object(
        service, "_stored_connection", return_value=_postgres_connection()
    ):
        try:
            service.test_connection(
                _postgres_connection(database="other"), replacing="database"
            )
        except ValueError as exc:
            assert "cannot be changed" in str(exc)
        else:
            raise AssertionError("expected a ValueError for the renamed database")


def test_update_connection_keeps_the_stored_secret_when_left_blank() -> None:
    """The UI never receives credentials, so it cannot send them back; a blank
    field means "unchanged" rather than "clear it"."""
    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "is_vault_configured", return_value=False),
        patch.object(service, "insert_connection") as insert_connection,
        patch.object(service, "_refresh_connection_caches"),
        patch.object(service, "trigger_ingest") as trigger_ingest,
    ):
        service.update_connection(
            database_name="database",
            connection=_postgres_connection(password="", user="renamed"),
        )

    updated = json.loads(insert_connection.call_args.kwargs["connection"])
    assert updated["password"] == "secret"
    assert updated["user"] == "renamed"
    # The table filter is untouched, so the ingested graph is still correct.
    trigger_ingest.assert_not_called()


def test_update_connection_reingests_even_when_a_cache_refresh_fails() -> None:
    """Caches are refreshed after the write lands, so a failure there must not
    swallow the ingest: the new filter is already stored, and a retry would
    compare it against itself and skip the ingest for good."""
    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "is_vault_configured", return_value=False),
        patch.object(service, "insert_connection"),
        patch.object(
            service,
            "invalidate_connectors_cache",
            side_effect=RuntimeError("cache unavailable"),
        ),
        patch.object(service, "trigger_ingest") as trigger_ingest,
    ):
        service.update_connection(
            database_name="database",
            connection=_postgres_connection(table_deny_regex="^tmp_"),
        )

    trigger_ingest.assert_called_once()


def test_update_connection_reingests_when_the_table_filter_changes() -> None:
    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "is_vault_configured", return_value=False),
        patch.object(service, "insert_connection"),
        patch.object(service, "_refresh_connection_caches"),
        patch.object(service, "trigger_ingest") as trigger_ingest,
    ):
        service.update_connection(
            database_name="database",
            connection=_postgres_connection(table_allow_regex="^fact_"),
        )

    trigger_ingest.assert_called_once()


def test_update_connection_rejects_changing_the_connector_type() -> None:
    """The ingested graph was built by the stored connector, so pointing the same
    catalog row at a different driver is a new connection, not an edit."""
    with patch.object(
        service, "_stored_connection", return_value=_postgres_connection()
    ):
        try:
            service.update_connection(
                database_name="database",
                connection=_postgres_connection(type="mysql"),
            )
        except ValueError as exc:
            assert "cannot be changed" in str(exc)
        else:
            raise AssertionError("expected a ValueError for the changed type")


def test_update_connection_reports_an_unknown_database_as_missing() -> None:
    with patch.object(service, "_stored_connection", return_value=None):
        try:
            service.update_connection(
                database_name="ghost", connection=_postgres_connection()
            )
        except LookupError as exc:
            assert "ghost" in str(exc)
        else:
            raise AssertionError("expected a LookupError for the unknown database")


def test_delete_connection_clears_the_stored_record() -> None:
    """The record has to go from this process. Leaving it to the ingestion
    service meant a delete did nothing whenever that service was unreachable,
    and the connection came back on the next page load."""
    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "is_vault_configured", return_value=False),
        patch.object(service, "clear_connection") as clear_connection,
        patch.object(service, "_refresh_connection_caches"),
        patch.object(service, "trigger_reset") as trigger_reset,
    ):
        result = service.delete_connection("database")

    clear_connection.assert_called_once_with(database_name="database")
    trigger_reset.assert_called_once_with("database")
    assert result == {"database_name": "database"}


def test_delete_connection_removes_the_vault_secret_before_the_row() -> None:
    """`list_connections` prefers a Vault secret over the row, so clearing the
    row first would resurrect the connection if the secret delete then failed."""
    calls: list[str] = []

    with (
        patch.object(
            service, "_stored_connection", return_value=_postgres_connection()
        ),
        patch.object(service, "is_vault_configured", return_value=True),
        patch.object(
            service, "delete_secrets", side_effect=lambda *_: calls.append("vault")
        ),
        patch.object(
            service, "clear_connection", side_effect=lambda **_: calls.append("row")
        ),
        patch.object(service, "_refresh_connection_caches"),
        patch.object(service, "trigger_reset"),
    ):
        service.delete_connection("database")

    assert calls == ["vault", "row"]


def test_delete_connection_reports_an_unknown_database_as_missing() -> None:
    with (
        patch.object(service, "_stored_connection", return_value=None),
        patch.object(service, "clear_connection") as clear_connection,
        patch.object(service, "trigger_reset") as trigger_reset,
    ):
        assert service.delete_connection("ghost") is None

    clear_connection.assert_not_called()
    trigger_reset.assert_not_called()
