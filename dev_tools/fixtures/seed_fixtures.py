# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Build every fixture database in one command.

Usage::

    docker compose up -d postgres
    uv run --no-sync python -m dev_tools.fixtures.seed_fixtures

See ``dev_tools/fixtures/sql/README.md`` for what each fixture covers and why.
"""

from __future__ import annotations

import logging

from dev_tools.fixtures import seed_local_postgres

logger = logging.getLogger("dev_tools.fixtures.seed_fixtures")


def main() -> None:
    logger.info("Seeding Postgres fixtures...")
    seed_local_postgres.seed()

    logger.info("All fixtures ready.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
