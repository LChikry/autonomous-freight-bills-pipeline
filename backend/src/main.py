from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from config import config
from api.v1 import ops, documents

logger = logging.getLogger(__name__)
logger.info("\n\n------------------------------ NEW INSTANCE ------------------------------")

app = FastAPI(
    title=config.app_name,
    docs_url=None if config.is_production else "/docs",
    redoc_url=None if config.is_production else "/redoc",
    openapi_url=None if config.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    
    logger.info(
        f"Path: {request.url.path} "
        f"Method: {request.method} "
        f"Status: {response.status_code} "
        f"Duration: {formatted_process_time}ms"
    )
    return response


@app.get("/")
def status_check():
    return {"is_ok": "ok"}


app.include_router(ops.router)
app.include_router(documents.router)
