# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

import time
from decimal import Decimal
from typing import Any

import pandas as pd
import pytest

from sql_agent.nodes import result_analyzer, sql_executor
from sql_agent.nodes import value_probe as probe
from sql_agent.nodes.safety_validator import (
    check_sql_safety,
    sql_safety_validator,
)
from sql_agent.state import State

TABLE = {
    "name": "fact_partisipasi_program",
    "schema_name": "iccn_dwh",
    "columns": [{"name": "provinsi"}, {"name": "nama_pendaftar"}],
}


class FakeConnector:
    def __init__(self, values: list[str]) -> None:
        self.values = values
        self.calls: list[tuple[str, list]] = []

    def qualify(self, schema: str, table: str) -> str:
        return f'"{schema}"."{table}"'

    def execute(self, sql: str, parameters: list, timeout_s: float) -> pd.DataFrame:
        self.calls.append((sql, parameters))
        return pd.DataFrame({"v": self.values, "s": [1.0] * len(self.values)})


def _state(**fields: Any) -> State:
    return State(
        user_query="berapa pendaftar dari bali",
        ontology={"path_state": {"relevant_tables": [TABLE]}},
        **fields,
    )


@pytest.mark.parametrize(
    ("sql", "status"),
    [
        ('SELECT "judul" FROM "t" WHERE "judul" ILIKE \'%update%\'', "safe"),
        ("DELETE FROM t", "unsafe"),
        ("SELECT 1; DROP TABLE t", "unsafe"),
    ],
)
def test_safety_reads_the_statement_not_its_words(sql: str, status: str) -> None:
    update = sql_safety_validator(_state(sql_query=sql))
    assert update["sql_safety_status"] == status
    assert check_sql_safety(_state(**update)) == status


def test_execution_failure_is_reported_with_its_sqlstate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sql_executor,
        "run_query",
        lambda sql, connector: {
            "success": False,
            "error": "boom",
            "error_code": "22P02",
        },
    )
    update = sql_executor.sql_executor(_state(sql_query="SELECT 1"))
    assert update["sql_execution_status"] == "failure"
    assert update["error_code"] == "22P02"


@pytest.mark.parametrize(
    ("rows", "sql", "route"),
    [
        ([], "SELECT 1", "empty"),
        ([{"n": 0}], "SELECT count(*) FROM t WHERE provinsi = 'BALI'", "empty"),
        ([{"n": Decimal(0)}], "SELECT count(*) FROM t", "success"),
        ([{"n": 3}], "SELECT count(*) FROM t WHERE provinsi = 'BALI'", "success"),
    ],
)
def test_empty_looking_results_are_probed_once(
    rows: list, sql: str, route: str
) -> None:
    state = _state(
        sql_query=sql,
        sql_execution_status="success",
        sql_execution_result={"data": rows},
    )
    assert sql_executor.check_sql_execution(state) == route
    state.value_probed = True
    assert sql_executor.check_sql_execution(state) == "success"


def test_probe_lists_real_values_for_filtered_columns() -> None:
    sql = 'SELECT count(*) FROM "iccn_dwh"."fact_partisipasi_program" WHERE provinsi = \'Bali\''
    connector = FakeConnector(["BALI", "BANTEN"])
    update = probe.value_probe(_state(sql_query=sql, connector=connector))
    assert update["value_probed"] and update["retry_count"] == 1
    assert "'BALI', 'BANTEN'" in update["retry_feedback"]
    assert connector.calls[0][1] == ["Bali"]
    assert '"provinsi"' in connector.calls[0][0]


def test_parallel_probes_keep_filter_order() -> None:
    class Slow(FakeConnector):
        def execute(self, sql: str, parameters: list, timeout_s: float) -> pd.DataFrame:
            # The first probe finishes last; lines must still follow the SQL.
            time.sleep(0.2 if parameters == ["Bali"] else 0)
            return pd.DataFrame({"v": [f"{parameters[0]}!"], "s": [1.0]})

    sql = (
        'SELECT count(*) FROM "iccn_dwh"."fact_partisipasi_program" '
        "WHERE provinsi = 'Bali' AND nama_pendaftar = 'Ani'"
    )
    feedback = probe.value_probe(_state(sql_query=sql, connector=Slow([])))[
        "retry_feedback"
    ]
    assert feedback.index("'Bali!'") < feedback.index("'Ani!'")


def test_probe_skips_tables_the_query_does_not_read() -> None:
    sql = "SELECT count(*) FROM other WHERE provinsi = 'Bali'"
    update = probe.value_probe(_state(sql_query=sql, connector=FakeConnector(["x"])))
    assert update == {"retry_feedback": None}
    assert probe.check_value_probe(_state(**update)) == "done"


def test_probe_failure_does_not_end_the_run() -> None:
    class Broken(FakeConnector):
        def execute(self, sql: str, parameters: list, timeout_s: float) -> pd.DataFrame:
            raise RuntimeError("down")

    sql = "SELECT 1 FROM fact_partisipasi_program WHERE provinsi = 'Bali'"
    assert probe.value_probe(_state(sql_query=sql, connector=Broken([]))) == {
        "retry_feedback": None
    }


def test_result_notes_words_the_retry_added(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(result_analyzer, "max_rows", lambda: 10)
    state = _state(
        sql_query="SELECT nama FROM t WHERE kota ILIKE '%denpasar%'",
        value_probed=True,
        sql_execution_result={"success": True, "data": [{"nama": "A"}]},
    )
    answer = result_analyzer.sql_result_analyzer(state)["answer"]
    assert answer.startswith("CATATAN : tidak ada yang cocok persis")
    assert "'denpasar'" in answer
