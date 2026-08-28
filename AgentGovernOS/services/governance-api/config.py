"""AgentGovern OS — Configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    app_name: str = "AgentGovern OS"
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://agentgovern:secret@localhost:5432/agentgovern"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # LLM Fallbacks
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    # Supabase (used by FreeBuff JWT validation)
    supabase_url: str = ""
    supabase_anon_key: str = ""


    # JWT Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # API Key Auth 
    # admin_api_key is the master bootstrap key (maps to ROLE_ADMIN)
    admin_api_key: str = ""
    # api_keys is a comma-separated list of KEY:ROLE pairs, e.g. "mykey1:operator,mykey2:auditor"
    api_keys: str = ""

    # Request Signing 
    # Falls back to jwt_secret_key when not set
    request_signing_secret: str = ""

    # Rate Limiting 
    rate_limit_enabled: bool = True    # Default to True for production security; can override via env
    rate_limit_default: int = 100       # Requests per window
    rate_limit_window_s: int = 60       # Window size in seconds

    # QICACHE
    qicache_ttl_days: int = 3
    qicache_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

@lru_cache
def get_settings() -> Settings:
    return Settings()
