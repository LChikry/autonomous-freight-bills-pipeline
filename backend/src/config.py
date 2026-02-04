import logging
import os
from pathlib import Path
from attrs import define, field, validators
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent # backend
load_dotenv(BASE_DIR / ".env")

def path_must_exist(instance, attribute, value):
    """Custom validator to check if a file path exists."""
    if not value.exists():
        raise FileNotFoundError(
            f"Missing required configuration file for '{attribute.name}': {value}"
        )

@define
class Config:
    app_name: str
    cors_origins: list[str]
    logging_level: int = field(default=logging.INFO)

    gmail_oauth_token_path: Path = field(
        default=BASE_DIR / "credentials" / "gmail_oauth_token.json",
    )
    
    gmail_oauth_client_path: Path = field(
        default=BASE_DIR / "credentials" / "gmail_oauth_client.json",
        validator=path_must_exist
    )
    
    firestore_client_path: Path = field(
        default=BASE_DIR / "credentials" / "firestore_service_account.json",
        validator=path_must_exist
    )

    anthropic_api_key: str = field(
        factory=lambda: os.environ["ANTHROPIC_API_KEY"],
    )

try:
    config = Config(
        app_name="BofL Analyzer",
        cors_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
    )
    
    logging.basicConfig(
        level=config.logging_level,
        format="%(asctime)s, %(name)-33s, %(levelname)-5s, %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Configuration loaded and set. App: {config.app_name}")

except (ValueError, FileNotFoundError, TypeError, KeyError) as e:
    logging.error(f"Error in Configuration..")
    exit(1)