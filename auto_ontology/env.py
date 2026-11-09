"""Environment bootstrap shared by all Auto Ontology process entrypoints."""

from pathlib import Path

from dotenv import load_dotenv

_repo_root = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Load the repo-root ``.env`` file into the process environment."""
    load_dotenv(_repo_root / ".env")
