import time
import contextvars
from contextlib import contextmanager, asynccontextmanager
from loguru import logger

__all__ = ["log_section", "log_call", "async_log_call"]

# Tracks the active hierarchy path (e.g., ["gmail", "messages.list"])
_active_namespace = contextvars.ContextVar("active_namespace", default=[])

@contextmanager
def log_section(namespace: str, **kwargs):
    assert "." not in namespace, "dot letter is reserved for nesting indicator"
    
    current_path = _active_namespace.get()
    new_path = current_path + [namespace]
    token = _active_namespace.set(new_path)
    
    # Prefix all kwargs for later serialization (e.g., "gmail.user_id": 123)
    prefix = ".".join(new_path)
    context_data = {f"{prefix}.{k}": v for k, v in kwargs.items()}
    context_data["_active_path"] = new_path
    
    with logger.contextualize(**context_data):
        try:
            yield
        finally:
            _active_namespace.reset(token)

@contextmanager
def log_call(service_name: str, **kwargs):
    """
    Context manager to standardize logging of external communications.
    """
    start_time = time.perf_counter()
    
    with log_section(service_name, **kwargs):
        try:
            yield
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                f"Succeeded outgoing request: {service_name}", 
                duration_ms=duration_ms, 
                succeed=True
            )
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                f"Failed outgoing request: {service_name}", 
                duration_ms=duration_ms, 
                succeed=False
            )
            raise


@asynccontextmanager
async def async_log_call(service_name: str, **kwargs):
    with log_call(service_name, **kwargs):
        yield