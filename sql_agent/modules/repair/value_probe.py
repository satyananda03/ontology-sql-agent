"""Hasil kosong: cari nilai yang benar-benar ada di kolom yang difilter."""

import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from typing import Any

import psycopg

from auto_ontology.utils.sql_identifiers import quoted_identifier
from sql_agent.core.logging import get_logger
from sql_agent.modules.sql.filters import extract_text_filters

logger = get_logger(__name__)

MAX_PROBES = 5
PROBE_LIMIT = 15
PROBE_VALUE_CHARS = 100
PROBE_TIMEOUT_S = 10.0
PROBE_WORKERS = 4
# ponytail: ranking without pg_trgm only sees this many distinct values, so a
# rare match in a high-cardinality column can be missed; install pg_trgm there.
FALLBACK_SCAN_LIMIT = 5000


def _clip(value: str) -> str:
    return value if len(value) <= PROBE_VALUE_CHARS else value[:PROBE_VALUE_CHARS] + "…"


def _probe_targets(
    sql: str, tables: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], str, str]]:
    """``(table, column, literal)`` for each text filter on a table the SQL reads."""
    targets = []
    for col, literal in extract_text_filters(sql):
        for table in tables:
            if re.search(rf"\b{re.escape(table['name'])}\b", sql) and any(
                c.get("name") == col for c in table.get("columns") or []
            ):
                targets.append((table, col, literal))
    return targets[:MAX_PROBES]


def _values(frame: Any) -> list[str]:
    return frame["v"].tolist() if len(frame) else []


def _similarity(literal: str, value: str) -> float:
    """Kemiripan 0..1 ala ``word_similarity``: mengandung kata yang dicari = cocok penuh."""
    needle, haystack = literal.lower(), value.lower()
    return (
        1.0 if needle in haystack else SequenceMatcher(None, needle, haystack).ratio()
    )


def _ranked_by_trigram(
    connector: Any, relation: str, column: str, literal: str
) -> list[str]:
    frame = connector.execute(
        f"SELECT DISTINCT {column}::text AS v, word_similarity(%s, {column}::text) AS s "
        f"FROM {relation} WHERE {column} IS NOT NULL "
        f"ORDER BY s DESC, v LIMIT {PROBE_LIMIT}",
        [literal],
        timeout_s=PROBE_TIMEOUT_S,
    )
    return _values(frame)


def _ranked_in_python(
    connector: Any, relation: str, column: str, literal: str
) -> list[str]:
    frame = connector.execute(
        f"SELECT DISTINCT {column}::text AS v FROM {relation} "
        f"WHERE {column} IS NOT NULL LIMIT {FALLBACK_SCAN_LIMIT}",
        timeout_s=PROBE_TIMEOUT_S,
    )
    ranked = sorted(_values(frame), key=lambda v: (-_similarity(literal, v), v))
    return ranked[:PROBE_LIMIT]


def _closest_values(
    connector: Any, table: dict[str, Any], col: str, literal: str
) -> list[str]:
    column = quoted_identifier(col, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    try:
        return _ranked_by_trigram(connector, relation, column, literal)
    except psycopg.errors.UndefinedFunction:
        logger.warning(
            "[VALUE-PROBE] pg_trgm tidak terpasang, ranking %s di Python", relation
        )
        return _ranked_in_python(connector, relation, column, literal)


def probe_lines(sql: str, tables: list[dict[str, Any]], connector: Any) -> list[str]:
    """Satu baris per kolom yang difilter: nilai terdekat yang ada di database."""
    targets = _probe_targets(sql, tables)
    with ThreadPoolExecutor(max_workers=min(len(targets), PROBE_WORKERS) or 1) as pool:
        found = list(pool.map(lambda t: _closest_values(connector, *t), targets))
    lines = []
    for (table, col, literal), closest in zip(targets, found, strict=True):
        values = ", ".join(f"'{_clip(v)}'" for v in closest)
        lines.append(
            f'- "{table.get("schema_name")}"."{table["name"]}"."{col}" '
            f"(dicari: '{literal}'): {values or '(kolom kosong)'}"
        )
    return lines


def probe_feedback(sql: str | None, lines: list[str]) -> str:
    """Umpan balik untuk generator: nilai nyata yang bisa dipakai menggantikan filter."""
    return (
        "<previous_attempt>\n"
        "Query sebelumnya dieksekusi tapi tidak menemukan data (0 baris atau hasil hitungan 0) :\n"
        f"{sql}\n\n"
        "Nilai yang benar-benar ada di database untuk kolom yang difilter (urut dari yang paling mirip dengan nilai yang dicari) :\n"
        + "\n".join(lines)
        + "\n\nTulis ulang query memakai nilai persis dari daftar di atas bila ada yang sesuai maksud pertanyaan."
        "Nilai berakhiran '…' adalah cuplikan teks panjang: filter kolom itu dengan ILIKE kata kunci khas, bukan =."
        "Jika tidak ada yang sesuai, pertahankan filternya — hasil kosong berarti datanya memang tidak ada.\n"
        "</previous_attempt>"
    )
