from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    rag_api_url: str = "http://localhost:8034"
    rag_api_key: str
    qolda_url: str = "http://localhost:23333"
    qolda_model: str = "issai/Qolda"
    qolda_max_tokens: int = 2048
    qolda_temperature: float = 0.7
    rag_top_k: int = 5
    backend_host: str = "0.0.0.0"
    backend_port: int = 8035
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
