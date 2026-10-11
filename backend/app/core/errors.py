from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, message: str, *, code: str = "app_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def _error_payload(
    *,
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: list[dict] | None = None,
) -> dict:
    request_id = getattr(request.state, "request_id", None)
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        },
        "status_code": status_code,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        payload = _error_payload(
            request=request,
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        payload = _error_payload(
            request=request,
            code="validation_error",
            message="Request validation failed.",
            status_code=422,
            details=exc.errors(),
        )
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        payload = _error_payload(
            request=request,
            code="http_error",
            message=str(exc.detail),
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content=payload)


__all__ = ["AppError", "register_exception_handlers"]
