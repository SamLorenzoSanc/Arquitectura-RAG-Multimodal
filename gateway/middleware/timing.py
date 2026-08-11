import time

from fastapi import FastAPI
from starlette.requests import Request
from core.logger import get_logger

logger = get_logger(__name__)


def register_logging_middleware(app: FastAPI):

    @app.middleware("http")
    async def log_requests(request: Request, call_next):

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_timing method=%s path=%s status=500 duration_ms=%.3f",
                request.method, request.url.path, elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.3f}"
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.3f}"
        logger.info(
            "request_timing method=%s path=%s status=%s duration_ms=%.3f",
            request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response