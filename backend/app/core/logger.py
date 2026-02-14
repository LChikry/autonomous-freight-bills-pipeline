import logging, sys, json, re
from loguru import logger

from .config import settings

__all__ = ["init_logger"]

def init_logger():
    _set_logger_intercept()
    logger.remove()
    logger.configure(extra={"trace_id": None})

    if settings.is_production:
        logger.add(
            sys.stdout,
            format=_log_serializer,
            level=settings.logging_level,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
        return
    
    logger.add(
        sys.stderr,
        format=_log_formatter,
        colorize=True,
        level=settings.logging_level,
        backtrace=True,
        diagnose=False,
    )


def _log_formatter(record):
    extra = record["extra"].copy()
    
    trace_id = str(extra.pop("trace_id", None))
    
    http_str = ""
    if "http" in extra:
        http = extra.pop("http")
        
        method = http.get("method", "")
        path = http.get("path", "")
        status = http.get("status", "")
        duration_ms = http.get("duration_ms", "")
        
        http_str = f"{method} {path} {status} in {duration_ms}ms"

    def recursive_formatter(current_key, maybe_dict):
        if not isinstance(maybe_dict, dict):
            return f"{current_key}=={maybe_dict}"
        
        results = []
        for k, v in maybe_dict.items():
            new_key = f"{current_key}.{k}"
            results.append(recursive_formatter(new_key, v))
        
        return "{" + ", ".join(results) + "}"

    leftovers_list = []
    if extra:
        for k, v in extra.items():
            # Generate string for this item
            item_str = recursive_formatter(k, v)
            leftovers_list.append(item_str)
    
    separator = "\n" + " " * 13 + " $ " # The vertical alignment
    leftovers_str = separator.join(leftovers_list)
    
    record["extra"]["http"] = (separator + http_str) if http_str else ""
    record["extra"]["leftovers"] = (separator + leftovers_str) if leftovers_list else ""
    record["message"] = separator + record["message"]
    
    return (
        "<m>{time:HH:mm:ss.SSSS}</m> | "
        f"<m>{trace_id.center(26, "*")}</m> | "
        "<level>{level: <8}</level> | "
        "<y>{name}</y>:<c>{function}</c>:<c>{line}</c>"
        "<level>{message}</level>"
        "{extra[http]}"
        "{extra[leftovers]}" 
        "\n\n"
    )


def _log_serializer(record):
    extra = record["extra"]
    
    log_entry = {
        **extra,
        "timestamp": record["time"].isoformat(),
        "log_level": record["level"].name,
        "message": record["message"],
        "service": {
            "name": settings.service_name,
            "version": settings.service_version,
            "env": settings.environment,
        },
        "log_path": {
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        },
    }
    
    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__,
            "message": str(record["exception"].value),
        }
    
    serialized = json.dumps(log_entry)
    return serialized.replace("{", "{{").replace("}", "}}") + "\n"


def _set_logger_intercept():
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

    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        uvi_logger = logging.getLogger(name)
        uvi_logger.handlers.clear()
        uvi_logger.propagate = False
        if name == "uvicorn.access": continue
        uvi_logger.addHandler(InterceptHandler())
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)