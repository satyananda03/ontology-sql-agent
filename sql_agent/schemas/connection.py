# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Kontrak API untuk koneksi database sumber dan ingest-nya."""

from pydantic import BaseModel


class SourceConnection(BaseModel):
    database: str
    host: str
    port: int
    user: str


class IngestStatus(BaseModel):
    running: bool
