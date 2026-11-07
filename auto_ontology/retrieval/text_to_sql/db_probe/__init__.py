# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Bounded, read-only database probing.

:class:`ProbeExecutor` is the single choke point that guarantees probes are
``SELECT``-only, ``LIMIT``-bounded, and capped by a call budget. Compilation
uses it to confirm semantic foreign keys against live values.
"""

from auto_ontology.retrieval.text_to_sql.db_probe.executor import (
    ProbeExecutor,
    is_read_only_select,
)

__all__ = ["ProbeExecutor", "is_read_only_select"]
