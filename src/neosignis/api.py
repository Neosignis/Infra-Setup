"""Authenticated stateless gateway; no signing content is persisted or logged."""

import asyncio
import json
import socket
from contextlib import asynccontextmanager
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from fastapi import Depends, FastAPI, HTTPException, Request as WebRequest
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .auth import Authenticator, Settings, bearer
from .contracts import Capabilities, RecognizeRequest, RecognizeResult, RenderRequest, RenderResult
from .http_common import ERRORS, configure, error


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WorkerTransport:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        # Internal model data must not follow redirects or environment HTTP proxies.
        self.opener = build_opener(NoRedirect(), ProxyHandler({}))

    def call(self, path, payload=None):
        encoded = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.base_url + path, data=encoded, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    return 502, None
                return response.status, json.loads(raw)
        except HTTPError as exc:
            # Never pass through arbitrary upstream error bodies/content.
            return exc.code if exc.code in {429, 503} else 502, None
        except (TimeoutError, socket.timeout):
            return 504, None
        except (URLError, OSError, ValueError):
            return 503, None


def create_app(settings=None, transport=None):
    @asynccontextmanager
    async def lifespan(app):
        config = settings or Settings.from_env()
        app.state.auth = Authenticator(config)
        app.state.transport = transport or WorkerTransport(config.inference_url)
        yield

    app = FastAPI(title="Neosignis engine API", version="0.1.0", lifespan=lifespan)
    configure(app)

    @app.exception_handler(HTTPException)
    async def auth_error(request: WebRequest, exc: HTTPException):
        response = error(exc.status_code, "unauthorized" if exc.status_code == 401 else "request_rejected", "Authentication required or request rejected")
        response.headers.update(exc.headers or {})
        return response

    async def principal(request: WebRequest, credentials=Depends(bearer)):
        return await request.app.state.auth.dependency(credentials)

    async def forward(path, result_type, payload=None):
        status, result = await asyncio.to_thread(app.state.transport.call, path, payload)
        if status != 200:
            codes = {429: "engine_busy", 503: "engine_unavailable", 504: "engine_timeout"}
            return error(status if status in codes else 502, codes.get(status, "invalid_engine_output"), "Engine could not provide a validated result")
        try:
            return result_type.model_validate(result)
        except (ValidationError, ValueError, TypeError):
            return error(502, "invalid_engine_output", "Engine response did not match its contract")

    @app.get("/healthz")
    def health():
        return {"status": "alive"}

    @app.get("/readyz", responses=ERRORS)
    async def ready():
        status, _ = await asyncio.to_thread(app.state.transport.call, "/readyz")
        if status != 200:
            return error(503, "engine_unavailable", "Engine is not ready")
        return {"status": "ready"}

    @app.get("/v1/capabilities", response_model=Capabilities, responses=ERRORS)
    async def capabilities(user=Depends(principal)):
        return await forward("/v1/capabilities", Capabilities)

    @app.post("/v1/recognize", response_model=RecognizeResult, responses=ERRORS)
    async def recognize(request: RecognizeRequest, user=Depends(principal)):
        result = await forward("/v1/recognize", RecognizeResult, request.model_dump(mode="json"))
        if not isinstance(result, JSONResponse) and result.language != request.language:
            return error(502, "invalid_engine_output", "Engine returned a different language")
        return result

    @app.post("/v1/render", response_model=RenderResult, responses=ERRORS)
    async def render(request: RenderRequest, user=Depends(principal)):
        result = await forward("/v1/render", RenderResult, request.model_dump(mode="json"))
        if not isinstance(result, JSONResponse) and (result.language != request.language or result.signer_id != request.signer_id):
            return error(502, "invalid_engine_output", "Engine returned a different language or signer")
        return result

    return app


app = create_app()
