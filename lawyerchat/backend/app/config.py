from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LawyerChat"
    debug: bool = True
    database_url: str
    embedding_model_name: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 5
    retrieval_mode: Literal["semantic", "hybrid"] = "hybrid"
    hybrid_semantic_weight: float = 0.60
    hybrid_keyword_weight: float = 0.30
    hybrid_metadata_weight: float = 0.10
    llm_provider: str = "deepseek"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.deepseek.com"
    llm_model_name: str = "deepseek-v4-flash"
    llm_temperature: float = 0.2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
