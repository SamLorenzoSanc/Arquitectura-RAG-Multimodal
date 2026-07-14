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