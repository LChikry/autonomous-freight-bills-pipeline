import logging
from attrs import define, field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s, %(name)-33s, %(levelname)-5s, %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)


@define
class Config:
    app_name: str
    cors_origins: list[str]


config = Config(
    app_name="BofL Analyzer",
    cors_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    )