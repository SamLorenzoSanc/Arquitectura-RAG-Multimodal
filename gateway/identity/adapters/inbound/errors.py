from fastapi import HTTPException

from shared.errors import AppError


def http_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)
