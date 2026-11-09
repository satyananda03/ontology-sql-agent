# SPDX-FileCopyrightText: Copyright (c) 2026, onto-sql contributors
# SPDX-License-Identifier: Apache-2.0

"""Propose synonyms for each Term, then store the ones a person approved.

Compilation only keeps aliases written out in a table description, and the UI shows
synonyms without editing them. So this takes two steps with a review between them::

    uv run python -m sql_agent.knowledge.generate_synonyms propose --out synonyms.yaml
    uv run python -m sql_agent.knowledge.generate_synonyms apply synonyms.yaml
"""

import argparse
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

_PROMPTS_FILE = Path(__file__).parents[1] / "prompts.yaml"


class SynonymProposal(BaseModel):
    synonyms: list[str] = Field(default_factory=list)


def clean_synonyms(term_name: str, proposed: list[str]) -> list[str]:
    """Trim, drop the Term's own name, and remove case-insensitive duplicates."""
    seen = {term_name.strip().casefold()}
    kept: list[str] = []
    for synonym in proposed:
        text = " ".join(str(synonym).split())
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            kept.append(text)
    return kept


def propose(terms: list[dict[str, Any]], llm: Any) -> dict[str, list[str]]:
    from auto_ontology.utils.llm_invoke import invoke_with_structured_output
    from auto_ontology.utils.prompt_loader import load_chat_prompt_template

    prompt = load_chat_prompt_template(_PROMPTS_FILE, "synonym_proposal")
    proposals: dict[str, list[str]] = {}
    for term in terms:
        messages = prompt.format_messages(
            name=term["name"],
            description=term.get("description") or "",
            table=term["table_name"],
            columns=", ".join(term.get("columns") or []),
        )
        result = invoke_with_structured_output(llm, messages, SynonymProposal)
        proposals[term["name"]] = clean_synonyms(
            term["name"], result.synonyms if result else []
        )
    return proposals


def _read_terms() -> list[dict[str, Any]]:
    from sqlalchemy import func, select

    from auto_ontology.dal import schema as s
    from auto_ontology.dal.session import store

    rows = store().query_read(
        select(
            s.term.c.id,
            s.term.c.name,
            s.term.c.description,
            s.catalog_table.c.name.label("table_name"),
            func.array_agg(s.catalog_column.c.name).label("columns"),
        )
        .select_from(
            s.term.join(s.table__term, s.table__term.c.term_id == s.term.c.id)
            .join(s.catalog_table, s.catalog_table.c.id == s.table__term.c.table_id)
            .join(s.catalog_column, s.catalog_column.c.table_id == s.catalog_table.c.id)
        )
        .where(s.catalog_column.c.data_type.is_distinct_from("vector"))
        .group_by(s.term.c.id, s.catalog_table.c.name)
    )
    return [dict(r) for r in rows]


def apply_synonyms(approved: dict[str, list[str]]) -> None:
    """Store reviewed synonyms and embed the Term and its attributes again."""
    from sqlalchemy import select

    from auto_ontology.dal import schema as s
    from auto_ontology.dal.session import store
    from auto_ontology.server.terms.service import refresh_term_embeddings

    for name, synonyms in approved.items():
        rows = store().query_read(select(s.term.c.id).where(s.term.c.name == name))
        if not rows:
            print(f"Skipped, no such Term: {name}")
            continue
        term_id = rows[0]["id"]
        store().query_write(
            s.term.update()
            .where(s.term.c.id == term_id)
            .values(synonyms=clean_synonyms(name, synonyms))
        )
        refresh_term_embeddings(term_id, refresh_dependent_attrs=True)
        print(f"Stored {len(synonyms)} synonym(s) for {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    proposer = commands.add_parser("propose", help="Write proposals for review.")
    proposer.add_argument("--out", type=Path, required=True)
    applier = commands.add_parser("apply", help="Store a reviewed file.")
    applier.add_argument("file", type=Path)
    args = parser.parse_args()

    load_dotenv(Path.cwd() / ".env")
    if args.command == "propose":
        from auto_ontology.utils.llm_invoke import get_llm_client

        proposals = propose(_read_terms(), get_llm_client())
        args.out.write_text(yaml.safe_dump(proposals, allow_unicode=True))
        print(f"Wrote {len(proposals)} Term(s) to {args.out}. Review it, then apply.")
    else:
        apply_synonyms(yaml.safe_load(args.file.read_text()))


if __name__ == "__main__":
    main()
