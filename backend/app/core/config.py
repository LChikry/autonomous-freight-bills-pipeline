from pathlib import Path
from typing import Literal
from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["settings", "Settings"]

_BASE_DIR = Path(__file__).resolve().parent.parent.parent # core->src->root

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BASE_DIR / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    service_name: str = "BofL Analyzer API"
    service_version: str = "v0.1.0"
    environment: Literal["dev", "prod"]
    cors_origins: list[str]
    
    anthropic_api_key: str
    gmail_token_path: Path = Field(default=_BASE_DIR / "credentials/gmail_token.json")
    gmail_client_path: FilePath = Field(default=_BASE_DIR / "credentials/gmail_client.json")
    firestore_client_path: FilePath = Field(default=_BASE_DIR / "credentials/firestore_client.json")
    
    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
    
    @property
    def logging_level(self) -> Literal["INFO", "DEBUG", "TRACE"]:
        return "INFO" if self.is_production else "DEBUG"


settings = Settings() # type: ignore
