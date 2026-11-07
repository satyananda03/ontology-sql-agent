# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pandas as pd
import pytest

from auto_ontology.catalog import ingest_config


def _tables() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "table_schema": ["dwh", "dwh", "raw"],
            "table_name": ["dim_user", "tmp", "dim_user"],
        }
    )


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "ingest.yaml"
    monkeypatch.setenv("INGEST_CONFIG_FILE", str(path))

    def write(text: str) -> None:
        path.write_text(text)

    return write


def test_a_missing_file_keeps_everything(config) -> None:
    [tables] = ingest_config.apply("db", _tables())
    assert len(tables) == 3


def test_an_unlisted_database_keeps_everything(config) -> None:
    config("databases: {other: {schemas: [dwh]}}")
    [tables] = ingest_config.apply("db", _tables())
    assert len(tables) == 3


def test_schemas_and_excluded_tables_apply_to_every_frame(config) -> None:
    config("databases: {db: {schemas: [DWH], exclude_tables: [tmp]}}")
    tables, columns = ingest_config.apply("db", _tables(), _tables())
    assert tables.to_dict("records") == [
        {"table_schema": "dwh", "table_name": "dim_user"}
    ]
    assert len(columns) == 1


def test_a_listed_schema_with_no_tables_raises_instead_of_emptying_the_catalog(
    config,
) -> None:
    config("databases: {db: {schemas: [typo]}}")
    with pytest.raises(ValueError, match="typo"):
        ingest_config.apply("db", _tables())


@pytest.mark.parametrize("text", ["databases: [db]", "databases: {db: {schemas: dwh}}"])
def test_a_malformed_file_raises(config, text: str) -> None:
    config(text)
    with pytest.raises(ValueError):
        ingest_config.apply("db", _tables())
