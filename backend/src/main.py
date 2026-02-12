from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import time, ulid

from config import config
from api.v1 import ops, documents

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
async def request_middleware(request: Request, call_next):
    """
    1. Add a unique UUID as the request_id to logger and sends it to client
    2. adds context data to logger such as method, path, client_ip and port, user-agent
    3. Record request process time, logs it and sends it to client
    4. catches unhandled exceptions, logs then and return a 500 HTTP code
    """
    start_time = time.perf_counter()
    
    context_data = {
        "request_id": request.headers.get("Request-ID", str(ulid.ULID())),
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown_ip",
        "client_port": request.client.port if request.client else "unknown_port",
        "http_protocol": f"HTTP/{request.scope.get('http_version', '1.1')}",
        "user_agent": request.headers.get("user-agent", "unknown_user_agent"),
    }
    with logger.contextualize(**context_data):
        logger.info(f"Request started: {context_data['method']} {context_data["path"]} via {context_data['http_protocol']}")
        
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"Unhandled Error", error_obj=exc)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal Server Error. Retry again later or notify our team."},
            )
        
        response.headers["Request-ID"] = context_data["request_id"]
        process_time_sec = time.perf_counter() - start_time
        response.headers["Request-Process-Time-Sec"] = str(process_time_sec)
        
        logger.info(
            f"Request completed: {response.status_code} {context_data['method']} {context_data["path"]} via {context_data['http_protocol']} within {process_time_sec:.5f}s",
            status_code=response.status_code,
            process_time_sec=f"{process_time_sec:.5f}"
        )
        return response


@app.get("/")
def status_check():
    return {"status": {
        "ok": True
    }}

app.include_router(ops.router)
app.include_router(documents.router)
