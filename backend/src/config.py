import logging, sys
from loguru import logger
from pathlib import Path
from typing import Literal
from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent 

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "BofL Analyzer"
    log_dir_path: Path = Field(default=BASE_DIR / "logs")
    cors_origins: list[str]
    environment: Literal["dev", "prod"]
    log_to_file: bool
    
    anthropic_api_key: str
    gmail_token_path: Path = Field(default=BASE_DIR / "credentials/gmail_token.json")
    gmail_client_path: FilePath = Field(default=BASE_DIR / "credentials/gmail_client.json")
    firestore_client_path: FilePath = Field(default=BASE_DIR / "credentials/firestore_client.json")
    
    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
    
    @property
    def logging_level(self) -> Literal["INFO", "DEBUG", "TRACE"]:
        return "INFO" if self.is_production else "TRACE"


def set_logger_intercept():
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    loggers_name = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]
    for logger_name in loggers_name:
        _logging_logger = logging.getLogger(logger_name)
        _logging_logger.handlers = [InterceptHandler()]
        _logging_logger.propagate = False
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


def setup_logger(config: Settings | None = None):
    set_logger_intercept()
    logger.remove()
    logger.configure(extra={"request_id": "N/A"})

    if config and config.is_production:
        if config.log_to_file:
            logger.add(
                config.log_dir_path / "app_{time:YYYY-MM-DD}.jsonl",
                rotation="00:00",
                retention="6 months",
                compression="tar.gz",
                serialize=True,
                level=config.logging_level,
                enqueue=True,
                backtrace=True,
                diagnose=False,
            )
        else:
            logger.add(
                sys.stdout,
                serialize=True,
                level=config.logging_level,
                enqueue=True,
                backtrace=True,
                diagnose=False,
            )
    else:
        dev_format = (
            "<green>{time:HH:mm:ss:SSS}</green> | "
            "<cyan>{extra[request_id]}</cyan> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "{extra}"
        )
        logger.add(
            sys.stderr,
            format=dev_format,
            colorize=True,
            level=config.logging_level if config else "TRACE",
            backtrace=True,
            diagnose=True,
        )

try:
    config = Settings() # type: ignore
    setup_logger(config)
    logger.success(f"Configuration loaded successfully")
except Exception as e:
    setup_logger()
    logger.exception("Configuration failed to load")
    exit(1)