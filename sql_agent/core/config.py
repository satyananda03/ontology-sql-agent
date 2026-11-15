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

# Dibaca ``llm_service.get_llm``. Kosong: tidak ada model di sini yang butuh perlakuan khusus.
#: model_id -> context window; membatasi ``max_input_tokens`` di profil model.
MODEL_CONTEXT_WINDOWS: dict[str, int] = {}
CONTEXT_BUDGET_TOKENS = 0
#: Model yang menolak ``temperature`` eksplisit.
MODELS_WITHOUT_TEMPERATURE: frozenset[str] = frozenset()
#: Model Amazon Nova, yang reasoning-nya dinyalakan lewat ``extra_body``.
NOVA_MODELS: frozenset[str] = frozenset()


class Settings(BaseSettings):
    # Env yang bernilai kosong dianggap tidak di-set, jadi default-nya yang berlaku.
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", extra="ignore", env_ignore_empty=True
    )

    # ─── Server ───
    log_level: str = "INFO"
    # Dipakai kedua service di run.py. Loopback: keduanya tanpa login.
    # Di dalam container set 0.0.0.0.
    bind_host: str = "127.0.0.1"
    api_port: int = 3001
    ingestion_port: int = 3002

    # ─── LLM ───
    llm_model: str | None = None
    llm_binding_host: str | None = None
    llm_binding_api_key: str | None = None
    llm_timeout: float = 120.0
    # Percobaan per panggilan model (LLM, embedding, rerank) untuk error sementara.
    max_retries: int = 3

    # ─── Embedding ───
    embedding_model: str | None = None
    embedding_binding_host: str | None = None
    embedding_binding_api_key: str | None = None
    embedding_timeout: float = 60.0

    # ─── Rerank ───
    rerank_model: str | None = None
    # URL endpoint rerank utuh, mis. ``https://host/v1/rerank``.
    rerank_binding_host: str | None = None
    rerank_binding_api_key: str | None = None
    rerank_timeout: float = 60.0

    # ─── SQL agent: POST /api/sql-agent/query ───
    # Model yang dipakai classic_sql_agent untuk generate, supaya keduanya sebanding.
    sql_agent_generator_model: str = "qwen.qwen3-coder-480b-a35b-v1:0"
    # Baris yang diserahkan ke agent pemanggil; sisanya dihitung, tidak ditampilkan.
    sql_agent_max_rows: int = 200
    # Detik sebelum tool melaporkan timeout, dan jumlah pertanyaan yang berjalan sekaligus.
    sql_agent_timeout_s: float = 120.0
    sql_agent_max_concurrent: int = 4
    # Berapa kali retrieval boleh diulang ketika tabel terpilih terbukti kurang.
    sql_agent_max_renavigations: int = 1
    # Timeout per request LLM, jauh di bawah anggaran 120 dtk route: satu panggilan
    # yang macet sebesar LLM_TIMEOUT sendirian menghabiskan anggaran satu tool call.
    # ponytail: retry (3x) masih mengalikan ini; deadline per run adalah upgrade-nya
    # bila run melewati anggaran.
    sql_agent_llm_timeout_s: float = 45.0
    # Hit vektor yang diserahkan tiap pencarian katalog ke reranker; 0 mematikannya.
    sql_agent_rerank_pool: int = 10


settings = Settings()
