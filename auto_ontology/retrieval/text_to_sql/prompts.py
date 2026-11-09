import os

# Controls how many entity noun phrases are extracted for SQL generation.
SQL_GEN_MAX_ENTITIES: int = int(os.environ.get("SQL_GEN_MAX_ENTITIES", "5"))
