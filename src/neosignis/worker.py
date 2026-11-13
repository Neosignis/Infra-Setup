"""Private engine host. Default deployment has no interpretation capabilities."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError

from .contracts import Capabilities, RecognizeRequest, RecognizeResult, RenderRequest, RenderResult
from .http_common import ERRORS, configure, error
from .providers import EngineUnavailable, load_provider


def create_app(provider=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.provider = provider if provider is not None else load_provider(os.getenv("ENGINE_PROVIDER", ""))
        Capabilities.model_validate(app.state.provider.capabilities())
        yield

    app = FastAPI(title="Neosignis private engine worker", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    configure(app)
    # Serial admission by default. Capacity is raised only after GPU/memory benchmarks.
    app.state.busy = False
    app.state.operations = set()

    @app.get("/healthz")
    def health():
        return {"status": "alive"}

    @app.get("/readyz", responses=ERRORS)
    def ready():
        caps = Capabilities.model_validate(app.state.provider.capabilities())
        if not any(c.approved and (c.recognize or c.render) for c in caps.languages):
            return error(503, "engine_unavailable", "No approved engine capabilities installed")
        return {"status": "ready"}

    @app.get("/v1/capabilities", response_model=Capabilities)
    def capabilities():
        return app.state.provider.capabilities()

    async def execute(kind, request, result_type, capability):
        try:
            result = await asyncio.to_thread(getattr(app.state.provider, kind), request)
            result = result_type.model_validate(result)
            if result.language != request.language:
                raise ValueError("Provider returned wrong language")
            if isinstance(result, RecognizeResult) and result.model_version != capability.model_version:
                raise ValueError("Provider returned an unadvertised model version")
            if isinstance(result, RenderResult) and result.signer_id != request.signer_id:
                raise ValueError("Provider returned wrong signer")
            return result
        except EngineUnavailable:
            return error(503, "engine_unavailable", "Approved provider is currently unavailable")
        except (ValidationError, ValueError, TypeError):
            return error(502, "invalid_engine_output", "Provider output violated its contract")
        except Exception:
            return error(503, "engine_failed", "Engine failed without producing a validated result")
        finally:
            app.state.busy = False

    async def invoke(kind, request, result_type):
        caps = Capabilities.model_validate(app.state.provider.capabilities())
        capability = next((c for c in caps.languages if c.language == request.language), None)
        if not capability or not capability.approved or not getattr(capability, kind):
            return error(503, "engine_unavailable", "Requested language capability is unavailable")
        if app.state.busy:
            return error(429, "engine_busy", "Worker is at its development admission limit")
        app.state.busy = True
        # A disconnected caller cannot release GPU admission while work continues.
        operation = asyncio.create_task(execute(kind, request, result_type, capability))
        app.state.operations.add(operation)
        operation.add_done_callback(app.state.operations.discard)
        return await asyncio.shield(operation)

    @app.post("/v1/recognize", response_model=RecognizeResult, responses=ERRORS)
    async def recognize(request: RecognizeRequest):
        return await invoke("recognize", request, RecognizeResult)

    @app.post("/v1/render", response_model=RenderResult, responses=ERRORS)
    async def render(request: RenderRequest):
        return await invoke("render", request, RenderResult)

    return app


app = create_app()
