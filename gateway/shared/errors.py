from __future__ import annotations


class AppError(Exception):
    """Error de aplicación que el adaptador HTTP traduce a HTTPException."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
