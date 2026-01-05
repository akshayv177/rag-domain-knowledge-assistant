from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API keys / models
    openai_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    # Paths
    docs_path: Path = Path("data/raw")
    vector_db_path: Path = Path("data/vector_store")

    # Where to read env vars / .env from
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
