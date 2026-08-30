from fastapi import HTTPException


class GatewayException(HTTPException):

    def __init__(self, detail="Gateway error", status_code=500):
        super().__init__(status_code=status_code, detail=detail)

class RagServiceUnavailable(GatewayException):

    def __init__(self):
        super().__init__(detail="RAG Service unavailable", status_code=503)

class DocumentNotFound(GatewayException):

    def __init__(self):
        super().__init__(detail="Document not found", status_code=404)

class UnauthorizedException(GatewayException):

    def __init__(self):
        super().__init__(detail="Unauthorized", status_code=401)

class AppError(Exception):
    """Error de aplicación que el adaptador HTTP traduce a HTTPException."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
