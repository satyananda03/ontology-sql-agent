"""The separation that keeps model access maintainable, checked on the source.

    model_config  reads the env  ->  llm_client / embedding / rerank  build clients
                                 ->  everything else asks those three

A rule that only lives in a docstring erodes one convenient shortcut at a time;
these fail the moment a file takes one.
"""

import re
from pathlib import Path

AUTO_ONTOLOGY = Path(__file__).resolve().parents[2]
REPO = AUTO_ONTOLOGY.parent

_BINDING_ENV = re.compile(
    r"(LLM|EMBEDDING|RERANK)_(MODEL|BINDING_HOST|BINDING_API_KEY)"
)
#: The only modules allowed to turn a binding into a client.
_CLIENT_MODULES = {"llm_client.py", "embedding.py", "rerank.py"}


def _sources(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.py")
        if "tests" not in path.parts and "__pycache__" not in path.parts
    ]


def test_only_model_config_reads_the_binding_env_vars() -> None:
    offenders = [
        f"{path.relative_to(REPO)}:{number}"
        for path in _sources(AUTO_ONTOLOGY)
        if path.name != "model_config.py"
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if "environ" in line and _BINDING_ENV.search(line)
    ]
    assert offenders == []


def test_only_the_client_modules_use_the_bindings() -> None:
    users = {
        path.name
        for path in _sources(AUTO_ONTOLOGY)
        if "utils.model_config import" in path.read_text()
    }
    assert users == _CLIENT_MODULES


def test_only_llm_client_builds_a_chat_client() -> None:
    builders = {
        path.name
        for path in _sources(AUTO_ONTOLOGY)
        if "ChatOpenAI(" in path.read_text()
    }
    assert builders == {"llm_client.py"}


def test_auto_ontology_does_not_depend_on_sql_agent() -> None:
    importers = [
        str(path.relative_to(REPO))
        for path in _sources(AUTO_ONTOLOGY)
        if re.search(r"^\s*(from|import) sql_agent\b", path.read_text(), re.M)
    ]
    assert importers == []


def test_the_nvidia_client_library_is_gone() -> None:
    importers = [
        str(path.relative_to(REPO))
        for root in (AUTO_ONTOLOGY, REPO / "sql_agent")
        for path in _sources(root)
        if "langchain_nvidia_ai_endpoints" in path.read_text()
    ]
    assert importers == []
    assert "langchain-nvidia-ai-endpoints" not in (REPO / "pyproject.toml").read_text()
