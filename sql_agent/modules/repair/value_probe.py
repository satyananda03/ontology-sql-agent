"""Hasil kosong: cari nilai yang benar-benar ada di kolom yang difilter."""
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from auto_ontology.utils.sql_identifiers import quoted_identifier
from sql_agent.modules.sql.filters import extract_text_filters

MAX_PROBES = 5
PROBE_LIMIT = 15
PROBE_VALUE_CHARS = 100
PROBE_TIMEOUT_S = 10.0
PROBE_WORKERS = 4

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

def _closest_values(
    connector: Any, table: dict[str, Any], col: str, literal: str
) -> list[str]:
    column = quoted_identifier(col, "postgres")
    relation = connector.qualify(table.get("schema_name"), table["name"])
    frame = connector.execute(
        f"SELECT DISTINCT {column}::text AS v, word_similarity(%s, {column}::text) AS s "
        f"FROM {relation} WHERE {column} IS NOT NULL "
        f"ORDER BY s DESC, v LIMIT {PROBE_LIMIT}",
        [literal],
        timeout_s=PROBE_TIMEOUT_S,
    )
    return frame["v"].tolist() if len(frame) else []

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