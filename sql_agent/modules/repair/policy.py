# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Kebijakan perbaikan: klasifikasi error, rute setelah gagal, dan teks umpan baliknya."""

import time
from collections.abc import Callable
from typing import Any, Literal

from sql_agent.core.config import settings
from sql_agent.core.logging import get_logger
from sql_agent.schemas import State

logger = get_logger(__name__)

ErrorKind = Literal["fixable", "transient", "fatal"]

MAX_RETRIES = 2
INFO_NOT_FOUND = "info_not_found"
MISSING_OBJECT_CODES = ("42703", "42P01")
NOT_AVAILABLE_MSG = ("Informasi ini tidak ada di tabel mana pun. Laporkan data tidak tersedia, jangan parafrase.")
_HINTS = {
    "42": "Nama tabel/kolom/fungsi atau tipe operand tidak cocok. Pakai persis nama dari konteks skema; cast eksplisit bila membandingkan tipe yang berbeda.",
    "22": "Error saat data diproses (cast, format tanggal, pembagian nol). Jangan cast kolom teks ke angka/tanggal tanpa memastikan formatnya; bungkus pembagi dengan NULLIF(x, 0).",
    "21000": "Subquery skalar mengembalikan lebih dari satu baris; ganti dengan IN, JOIN, atau agregasi.",
    "57014": "Query melewati batas waktu. Persempit dengan filter, agregasi sebelum JOIN, dan hindari ILIKE pada kolom teks panjang tanpa filter lain.",
    "0A": "Konstruksi SQL ini tidak didukung; tulis ulang dengan SQL standar.",
}
_FAILURE_GUIDANCE = {
    "fixable": "Query tetap gagal setelah diperbaiki otomatis. Persempit atau perjelas pertanyaan (entitas, wilayah, periode. dll), lalu panggil tool ini lagi.",
    "transient": "Gangguan koneksi database, bukan karena kata-kata pertanyaan. Coba sekali lagi; kalau tetap gagal, laporkan database sedang tidak tersedia.",
    "fatal": "Ditolak karena batasan akses/konfigurasi, bukan karena kata-kata pertanyaan. Jangan parafrase; laporkan data tersebut tidak tersedia.",
}

def classify_error(sqlstate: str | None) -> ErrorKind:
    """Tentukan apakah mengulang ada gunanya, dan dengan cara apa."""
    if (
        sqlstate is None
        or sqlstate.startswith(("08", "53", "57P"))
        or sqlstate in ("40001", "40P01")
    ):
        return "transient"
    if sqlstate == "42501":
        return "fatal"
    if sqlstate.startswith(("42", "22", "0A")) or sqlstate in ("21000", "57014"):
        return "fixable"
    return "fatal"

def can_renavigate(state: State) -> bool:
    return state.renavigation_count < settings.sql_agent_max_renavigations

def _hint(code: str | None) -> str:
    code = code or ""
    return _HINTS.get(code) or _HINTS.get(code[:2], "")

def retry_transient(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    result = call()
    if result.get("error") and classify_error(result.get("error_code")) == "transient":
        logger.warning(
            f"[REPAIR] gangguan sementara, ulangi sekali: {result['error'][:200]}"
        )
        time.sleep(1)
        result = call()
    return result

def route_failure(state: State) -> Literal["repair", "renavigate", "fail"]:
    kind = classify_error(state.error_code)
    if kind != "fixable":
        return "fail"
    if state.retry_count >= MAX_RETRIES:
        logger.warning("[REPAIR] jatah perbaikan habis")
    elif state.error == state.last_error:
        logger.warning("[REPAIR] error yang sama berulang")
    else:
        return "repair"
    if state.error_code in MISSING_OBJECT_CODES and can_renavigate(state):
        return "renavigate"
    return "fail"

def repair_feedback(state: State) -> str:
    """Umpan balik untuk generator setelah eksekusi gagal dengan error yang bisa diperbaiki."""
    hint = _hint(state.error_code)
    return (
        "<previous_attempt>\n"
        f"Query sebelumnya gagal dengan error Postgres [{state.error_code}]:\n"
        f"{state.error}\n\n"
        f"SQL:\n{state.raw_sql_query or state.sql_query}\n\n"
        + (f"Petunjuk: {hint}\n" if hint else "")
        + "Perbaiki query agar tetap menjawab pertanyaan yang sama. Pakai hanya tabel dan kolom yang ada di konteks skema.\n"
        "</previous_attempt>"
    )

def failure_answer(state: State) -> str:
    """Pesan akhir yang memberi tahu agent pemanggil apakah mengulang ada gunanya."""
    sql = state.raw_sql_query or state.sql_query
    if state.error_code == INFO_NOT_FOUND or state.error_code in MISSING_OBJECT_CODES:
        guidance = NOT_AVAILABLE_MSG
    else:
        guidance = _FAILURE_GUIDANCE[classify_error(state.error_code)]
    return (
        "STATUS: error\n"
        + (f"SQL: {sql.strip()}\n" if sql else "")
        + f"ERROR: {state.error}\n"
        + guidance
    )