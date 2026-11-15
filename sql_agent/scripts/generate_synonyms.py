# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Propose synonyms for each Term, then store the ones a person approved.

Two steps with a review between them (from the repo root)::

    uv run python -m sql_agent.scripts.generate_synonyms propose --out synonyms.yaml
    uv run python -m sql_agent.scripts.generate_synonyms apply synonyms.yaml
"""

import argparse
import asyncio
from pathlib import Path

import yaml

from auto_ontology.env import load_env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    proposer = commands.add_parser("propose", help="Write proposals for review.")
    proposer.add_argument("--out", type=Path, required=True)
    applier = commands.add_parser("apply", help="Store a reviewed file.")
    applier.add_argument("file", type=Path)
    args = parser.parse_args()

    load_env()
    # Imported after load_env: auto_ontology reads its settings at import time.
    from sql_agent.modules.knowledge import synonyms

    if args.command == "propose":
        proposals = asyncio.run(synonyms.propose(synonyms.read_terms()))
        args.out.write_text(yaml.safe_dump(proposals, allow_unicode=True))
        print(f"Wrote {len(proposals)} Term(s) to {args.out}. Review it, then apply.")
    else:
        synonyms.apply_synonyms(yaml.safe_load(args.file.read_text()))


if __name__ == "__main__":
    main()
