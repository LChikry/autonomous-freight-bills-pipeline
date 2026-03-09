import time
import ulid
from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger


async def request_logger_middleware(request: Request, call_next):
    """
    1. Add a unique UUID as the request_id to logger and sends it to client
    2. adds context data to logger such as method, path, client_ip and port, user-agent
    3. Record request process time, logs it and sends it to client
    4. catches unhandled exceptions, logs then and return a 500 HTTP code
    """
    start_time = time.perf_counter()
    
    trace_id = request.headers.get("X-Trace-Id", str(ulid.ULID()))
    http_context = {
        "method": request.method,
        "path": request.url.path,
        "user_agent": request.headers.get("user_agent"),
    }
    
    with logger.contextualize(trace_id=trace_id):
        logger.info(f"Request started", http=http_context)
        
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"Unhandled Error", error=exc)
            
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal Server Error. Retry again later or notify our team."},
            )
        
        http_context["status"] = str(response.status_code)
        http_context["duration_ms"] = str(round((time.perf_counter() - start_time) * 1000, 2))
        
        logger.info("Request completed", http=http_context)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = http_context["duration_ms"]
        return response