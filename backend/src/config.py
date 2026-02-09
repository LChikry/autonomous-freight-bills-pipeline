
import logging
from pathlib import Path
from typing import Literal
from pydantic import Field, computed_field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent 

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "BofL Analyzer"
    log_filepath: Path = Field(default=BASE_DIR / "app.log")
    cors_origins: list[str] = []
    environment: Literal["development", "production"] = "development"
    
    anthropic_api_key: str  = ""
    gmail_token_path: Path = Field(default=BASE_DIR / "credentials/gmail_token.json")
    gmail_client_path: FilePath = Field(default=BASE_DIR / "credentials/gmail_client.json")
    firestore_client_path: FilePath = Field(default=BASE_DIR / "credentials/firestore_client.json")
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def logging_level(self) -> int:
        return logging.INFO if self.is_production else logging.DEBUG

try:
    config = Settings()

    logging.basicConfig(
        level=config.logging_level,
        format="%(asctime)s, %(name)-33s, %(levelname)-5s, %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        handlers=[
            logging.FileHandler(config.log_filepath),
            logging.StreamHandler(),
        ]
    )

    logging.info(f"Configuration loaded. App: {config.app_name}")

except Exception as e:
    print("-----------------CRITICAL CONFIGURATION ERROR:-----------------")
    print(e)
    exit(1)