from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core import settings, init_logger
from app.middlewares.request_logging import request_logger_middleware
from app.api.v1 import ops, documents


init_logger()
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logger()
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # app.add_middleware(BaseHTTPMiddleware, dispatch=request_logger_middleware)

    app.include_router(ops.router)
    app.include_router(documents.router)
    return app


app = create_app()

@app.get("/")
def status_check():
    return {"appStatus": {
        "allOk": True
    }}