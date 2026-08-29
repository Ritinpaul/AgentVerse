import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentStore Foundation Registry"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # Database Configuration (defaults to local sqlite for dev, postgresql for non-dev)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./agentstore.db"
        if os.getenv("APP_ENV", "development").lower() == "development"
        else "postgresql://postgres:postgres@localhost:5432/agentverse",
    )
    
    # Elasticsearch Configuration
    ELASTICSEARCH_URL: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    USE_ELASTICSEARCH: bool = os.getenv("USE_ELASTICSEARCH", "False").lower() in ("true", "1", "yes")
    
    # File storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    SCHEMA_PATH: Path = Path(__file__).resolve().parent / "schemas" / "agent.yaml.schema.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
