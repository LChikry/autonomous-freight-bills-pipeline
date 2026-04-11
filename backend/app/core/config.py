from pathlib import Path
from typing import Literal
from pydantic import Field, FilePath, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings", "Settings"]

_BASE_DIR = Path(__file__).resolve().parent.parent.parent # core->app->root
# assert Path.cwd() == _BASE_DIR, "You must run the program from the backend directory"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BASE_DIR / ".env",
        env_ignore_empty=True,
        env_file_encoding='utf-8',
        extra="ignore",
    )

    service_name: str = "AI-Powered Logistics Document Pipeline API"
    service_version: str = "v0.1.0"
    environment: Literal["dev", "prod"]
    cors_origins: list[str]
    
    llm_provider_name: str
    llm_model_name: str
    openai_api_key: SecretStr | None
    anthropic_api_key: SecretStr | None
    
    gmail_token_path: Path = Field(default=_BASE_DIR / "credentials/gmail_token.json")
    gmail_client_path: FilePath = Field(default=_BASE_DIR / "credentials/gmail_client.json")
    firestore_client_path: FilePath = Field(default=_BASE_DIR / "credentials/firestore_client.json")
    
    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
    
    @property
    def logging_level(self) -> str:
        return "INFO" if self.is_production else "DEBUG"


settings = Settings() # type: ignore
