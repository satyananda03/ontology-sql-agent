"""Propose synonyms for each Term, then store the ones a person approved."""
from typing import Any
from sql_agent.core.config import settings
from sql_agent.schemas import SynonymProposal
from sql_agent.services.llm_service import ainvoke_parsed, get_llm, structured_chain
from sql_agent.services.prompt_service import PROMPTS_FILE

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

async def propose(terms: list[dict[str, Any]]) -> dict[str, list[str]]:
    chain = structured_chain(
        get_llm(settings.llm_model, max_tokens=5000),
        PROMPTS_FILE,
        "synonym_proposal",
        SynonymProposal,
    )
    proposals: dict[str, list[str]] = {}
    for term in terms:
        result = await ainvoke_parsed(
            chain,
            {
                "name": term["name"],
                "description": term.get("description") or "",
                "table": term["table_name"],
                "columns": ", ".join(term.get("columns") or []),
            },
        )
        proposals[term["name"]] = clean_synonyms(
            term["name"], result.synonyms if result else []
        )
    return proposals


def read_terms() -> list[dict[str, Any]]:
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