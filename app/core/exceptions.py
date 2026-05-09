from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import traceback


# Custom exceptions
class NotFoundException(HTTPException):
    def __init__(self, error_message: str = "Resource not found", error_detail=None):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=error_message)
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}

class BadRequestException(HTTPException):
    def __init__(self, error_message: str = "Bad request", error_detail=None):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}


class UnauthorizedException(HTTPException):
    def __init__(self, error_message: str = "Unauthorized", error_detail=None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}


class ForbiddenException(HTTPException):
    def __init__(self, error_message: str = "Forbidden", error_detail=None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}


class ConflictException(HTTPException):
    def __init__(self, error_message: str = "Resource already exists", error_detail=None):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=error_message)
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}

class InternalServerException(HTTPException):
    def __init__(self, error_message: str = "Internal server error", error_detail=None):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
        self.error_detail = error_detail

    def to_dict(self):
        return {"message": self.detail, "error_detail": self.error_detail}

# Register exception handlers on the app
def register_exception_handlers(app: FastAPI):

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": "Validation error", "errors": errors},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        tb = traceback.format_exc()
        print(f"HTTP error: {exc.status_code} - {exc.detail}\n{tb}")
        if hasattr(exc, "to_dict"):
            content = exc.to_dict()
        else:
            content = {
                "message": exc.detail,
                "error_detail": {
                    "status_code": exc.status_code,
                    "error_type": type(exc).__name__,
                    "method": request.method,
                    "url": str(request.url),
                    "content_type": request.headers.get("content-type", "unknown"),
                    "hint": "If uploading files, use multipart/form-data, not application/json",
                },
            }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        print(f"Unhandled error: {type(exc).__name__}: {exc}\n{tb}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=InternalServerException(
                error_detail={
                    "error_type": type(exc).__name__,
                    "cause": str(exc),
                    "stack_trace": tb.splitlines(),
                }
            ).to_dict(),
        )
