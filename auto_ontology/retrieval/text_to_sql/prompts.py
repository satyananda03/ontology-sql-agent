# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os

# Controls how many entity noun phrases are extracted for SQL generation.
SQL_GEN_MAX_ENTITIES: int = int(os.environ.get("SQL_GEN_MAX_ENTITIES", "5"))


CUSTOM_ANALYSIS_RELEVANCE_FILTER_PROMPT = """You are a database domain expert.
Given a user's question and retrieved custom analyses, decide which analyses
are NOT relevant to answering the question.

Rules:
- Only remove an analysis if you are confident it is NOT needed.
- When in doubt, keep it — it is safer to include an extra analysis
  than to remove a necessary one.
- Consider both the analysis description AND its SQL when judging relevance.

User's question:
{question}

Retrieved custom analyses:
{analyses_summary}

Return the names of analyses to REMOVE. If unsure, return an empty list."""


TABLE_RELEVANCE_FILTER_PROMPT = """You are a database schema expert.
Given a user's question and a list of candidate tables, decide which tables
are actually needed to answer the question.

Rules:
- Only remove tables you are confident are NOT needed in the SQL query.
- A table can be required even when none of its columns appear in the answer:
  joining it may restrict WHICH rows qualify (only schools that appear in
  frpm; only patients who have an examination record). "No column of mine is
  returned" is NOT a reason to remove a table.
- Before removing a table, confirm BOTH: (a) it supplies no column the answer
  needs, AND (b) removing it cannot change the set of rows that qualify.
  Report both per table — a table stays unless both hold.
- If table A must be joined through tables B and C to reach table D, do NOT
  remove any table in the join chain (A, B, C, or D). The join paths below
  show real table connections. Keep the full bridges between tables that
  you deem relevant.
- If a selected custom analysis references a table in its SQL, do NOT
  remove that table.
- When in doubt, do NOT remove — it is safer to include an extra table
  than to remove a necessary one.

{domain_rules}{custom_analyses}{join_paths}{enriched_question}User's question:
{question}

Candidate tables:
{tables_summary}

Provide brief reasoning (1-2 sentences), then for each table you want REMOVED
give its name together with both removal checks: whether it supplies no column
the answer needs, and whether removing it cannot change which rows qualify.
State in its justification how you verified the row-scoping check.
Only remove a table if you are confident it is not needed. When in doubt, do NOT remove."""
