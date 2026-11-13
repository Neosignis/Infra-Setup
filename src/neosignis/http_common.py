"""Content-free error responses and bounded request bodies."""

import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .contracts import ErrorResponse


ERRORS = {code: {"model": ErrorResponse} for code in (401, 403, 413, 422, 429, 502, 503, 504)}


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


class BodyLimitMiddleware:
    """Enforce actual bytes, including chunked requests, before JSON parsing."""

    def __init__(self, app, max_bytes=4 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                payload = json.dumps({"error": {"code": "payload_too_large", "message": "Request exceeds 4 MiB"}}).encode()
                await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json")]})
                return await send({"type": "http.response.body", "body": payload})
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def configure(app: FastAPI):
    app.add_middleware(BodyLimitMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic errors can echo signing/text input; never return them verbatim.
        return error(422, "invalid_request", "Request does not match the versioned contract")
