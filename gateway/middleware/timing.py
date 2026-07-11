import time

from fastapi import FastAPI
from starlette.requests import Request
from gateway.core.logger import get_logger

logger = get_logger(__name__)


def register_logging_middleware(app: FastAPI):

    @app.middleware("http")
    async def log_requests(request: Request, call_next):

        start = time.perf_counter()

        response = await call_next(request)

        elapsed = time.perf_counter() - start

        logger.info(
            "%s %s | %s | %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )

        return response