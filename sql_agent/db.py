# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Validasi dan eksekusi SQL lewat konektor auto_ontology.

Satu koneksi read-only (``CONNECTION_STRINGS``) dipakai untuk semuanya, dengan
timeout dari ``execute_chat_sql``. Keluarannya sama dengan versi asyncpg classic,
jadi node di atasnya tidak perlu tahu drivernya berganti.
"""

from typing import Any

from auto_ontology.connectors.base import StatementTimeout
from auto_ontology.retrieval.text_to_sql.chat_sql import execute_chat_sql

# SQLSTATE query_canceled: classify_error menganggapnya bisa diperbaiki dengan
# mempersempit query, bukan gangguan sementara yang cukup diulang.
_TIMEOUT_SQLSTATE = "57014"


def db_error(error: Exception) -> tuple[str | None, str]:
    """``(sqlstate, pesan)`` dari exception DB. HINT Postgres ("Perhaps you meant
    ...") disertakan — itu petunjuk perbaikan paling berharga untuk generator."""
    if isinstance(error, StatementTimeout):
        return _TIMEOUT_SQLSTATE, str(error)
    message = str(error)
    hint = getattr(getattr(error, "diag", None), "message_hint", None)
    if hint and hint not in message:
        message += f"\nHINT: {hint}"
    return getattr(error, "sqlstate", None), message


def run_query(query: str, connector: Any) -> dict[str, Any]:
    """Execute SQL query and return formatted results."""
    result: dict[str, Any] = {
        "success": False,
        "data": None,
        "row_count": 0,
        "error": None,
        "error_code": None,
        "query_executed": query.strip(),
    }
    try:
        frame = execute_chat_sql(connector, query)
    except Exception as error:  # noqa: BLE001 — every driver error goes to repair
        result["error_code"], result["error"] = db_error(error)
        return result
    # NULL must reach the caller as null: pandas reads it back as NaN, which
    # json.dumps would write out as the invalid literal NaN.
    rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
    result.update(success=True, data=rows, row_count=len(rows))
    return result
