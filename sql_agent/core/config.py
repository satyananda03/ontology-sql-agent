"""Setting aplikasi: satu-satunya tempat sql_agent membaca environment.

Nama field = nama env (tidak peka huruf besar/kecil), dibaca dari environment proses lalu
``.env`` di root repo. File itu sengaja tidak dimuat ke ``os.environ`` di sini: auto_ontology
membaca variabelnya sendiri dari ``os.environ``, dan itu tugas entry point
(``sql_agent/main.py``, script CLI) lewat ``auto_ontology.env.load_env``. Kalau dimuat saat
import, test yang hanya meng-import modul ini ikut tersambung ke database asli.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_CONTEXT_WINDOWS: dict[str, int] = {}
CONTEXT_BUDGET_TOKENS = 0
MODELS_WITHOUT_TEMPERATURE: frozenset[str] = frozenset()
NOVA_MODELS: frozenset[str] = frozenset()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore", env_ignore_empty=True)
    # ─── Server ───
    log_level: str = "INFO"
    bind_host: str = "127.0.0.1"
    api_port: int = 3001
    ingestion_port: int = 3002
    # ─── LLM ───
    llm_model: str | None = None
    llm_binding_host: str | None = None
    llm_binding_api_key: str | None = None
    llm_timeout: float = 120.0
    max_retries: int = 3
    # ─── Embedding ───
    embedding_model: str | None = None
    embedding_binding_host: str | None = None
    embedding_binding_api_key: str | None = None
    embedding_timeout: float = 60.0
    # ─── Rerank ───
    rerank_model: str | None = None
    rerank_binding_host: str | None = None
    rerank_binding_api_key: str | None = None
    rerank_timeout: float = 60.0
    # ─── SQL agent: POST /api/sql-agent/query ───
    sql_agent_generator_model: str = "qwen.qwen3-coder-480b-a35b-v1:0"
    sql_agent_max_rows: int = 200
    sql_agent_timeout_s: float = 120.0
    sql_agent_max_concurrent: int = 4
    sql_agent_max_renavigations: int = 1
    sql_agent_llm_timeout_s: float = 45.0
    sql_agent_rerank_pool: int = 10

settings = Settings()