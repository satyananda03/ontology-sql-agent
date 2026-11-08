# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CustomAnalysis write orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from auto_ontology.server.custom_analyses import service


@patch("auto_ontology.server.custom_analyses.service.embed_custom_analyses")
@patch("auto_ontology.server.custom_analyses.service.fetch_database_name_for_analysis")
@patch("auto_ontology.vdb.get_semantic_vdb")
@patch("auto_ontology.utils.get_embed_params")
def test_embed_scopes_the_row_to_the_referenced_database(
    _embed_params: MagicMock,
    _vdb: MagicMock,
    fetch_database: MagicMock,
    embed: MagicMock,
) -> None:
    fetch_database.return_value = "WWI"

    service._embed_analysis("analysis-1")

    assert embed.call_count == 1
    assert embed.call_args.kwargs["database_name"] == "WWI"
    assert embed.call_args.kwargs["analysis_id"] == "analysis-1"


@patch("auto_ontology.server.custom_analyses.service.embed_custom_analyses")
@patch("auto_ontology.server.custom_analyses.service.fetch_database_name_for_analysis")
@patch("auto_ontology.vdb.get_semantic_vdb")
@patch("auto_ontology.utils.get_embed_params")
def test_unresolvable_database_still_embeds_but_warns(
    _embed_params: MagicMock,
    _vdb: MagicMock,
    fetch_database: MagicMock,
    embed: MagicMock,
) -> None:
    fetch_database.return_value = None

    service._embed_analysis("analysis-3")

    assert embed.call_count == 1
    assert embed.call_args.kwargs["database_name"] is None


@patch("auto_ontology.server.custom_analyses.service.get_schemas", return_value={})
@patch("auto_ontology.server.custom_analyses.service.get_dialects", return_value={})
def test_sql_the_catalog_cannot_resolve_raises_the_error_routes_answer_422(
    _dialects: MagicMock, _schemas: MagicMock
) -> None:
    """``validate_sql`` raises the base parse error; the routes catch only the
    subclass, so letting the base through turned a bad query into a 500."""
    with pytest.raises(service.CustomAnalysisSqlError):
        service.validate_custom_analysis_sql("SELECT 1")
