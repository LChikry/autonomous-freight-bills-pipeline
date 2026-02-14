import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import settings, init_logger
from app.middlewares import request_logger_middleware
from app.api.v1 import ops, documents


init_logger()
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logger()
    yield

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
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logger_middleware)


@app.get("/")
def status_check():
    return {"appStatus": {
        "allOk": True
    }}

app.include_router(ops.router)
app.include_router(documents.router)


if __name__ == "__main__":
    if settings.is_production:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            reload=False,
            log_config=None,
        )
    else:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_config=None,
        )