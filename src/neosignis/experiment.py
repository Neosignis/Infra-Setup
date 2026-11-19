"""Loopback-only experimental buffered-video service, separate from approved APIs."""
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

MAX_BYTES = 16 * 1024**2
PHASES = {'loading_pose', 'detecting', 'loading_model', 'translating'}


class Segment(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    start_ms: int = Field(ge=0, le=30000)
    end_ms: int = Field(ge=0, le=30000)

    @model_validator(mode='after')
    def ordered(self):
        if self.end_ms < self.start_ms:
            raise ValueError('Invalid activity interval')
        return self


class ExperimentResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    disposition: Literal['abstained', 'needs_review']
    reason: str = Field(pattern=r'^[a-z_]{1,60}$')
    candidate_text: str | None = Field(default=None, max_length=512)
    translated_text: None = None
    confidence: None = None
    quality_validated: Literal[False]
    segments: list[Segment] = Field(default_factory=list, max_length=20)
    elapsed_s: float = Field(default=0, ge=0)

    @model_validator(mode='after')
    def honest_outcome(self):
        if self.disposition == 'needs_review' and not (self.candidate_text and self.candidate_text.strip()):
            raise ValueError('Unverified suggestion requires candidate text')
        if self.disposition == 'abstained' and self.candidate_text is not None:
            raise ValueError('Abstention cannot expose guessed text')
        return self


def create_app(backend=None, *, web_port=5173):
    @asynccontextmanager
    async def lifespan(app):
        if backend is None:
            from .training.browser_backend import BrowserBackend
            app.state.backend = BrowserBackend(os.getenv('NEOSIGNIS_MODEL_ROOT', str(Path(__file__).resolve().parents[2] / 'data/local/models/unisign')))
        else:
            app.state.backend = backend
        app.state.busy = False
        app.state.jobs = {}
        app.state.operations = set()
        yield
        if app.state.operations:
            await asyncio.gather(*app.state.operations)

    app = FastAPI(title='Neosignis local experiment', lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware('http')
    async def local_only(request, call_next):
        host = request.url.hostname
        origin = request.headers.get('origin')
        allowed_origins = {f'http://127.0.0.1:{web_port}', f'http://localhost:{web_port}'}
        if host not in {'127.0.0.1', 'localhost', '::1'} or (origin and origin not in allowed_origins):
            return JSONResponse({'error': 'Local origin required'}, 403)
        if request.url.path != '/healthz' and request.headers.get('x-neosignis-request') != '1':
            return JSONResponse({'error': 'Local request header required'}, 403)
        return await call_next(request)

    @app.get('/healthz')
    def health():
        return {'status': 'alive'}

    @app.get('/status')
    def status():
        return {'available': app.state.backend.available(), 'busy': app.state.busy,
                'mode': 'experimental_buffered_video', 'quality_validated': False,
                'confidence_calibrated': False, 'max_duration_ms': 30000, 'max_bytes': MAX_BYTES}

    @app.post('/jobs')
    async def submit(request: Request):
        if not app.state.backend.available():
            return JSONResponse({'error': 'Local model assets unavailable'}, 503)
        if app.state.busy:
            return JSONResponse({'error': 'Another message is still processing'}, 429)
        mime = request.headers.get('content-type', '').split(';')[0].strip()
        if mime not in {'video/webm', 'video/mp4'}:
            return JSONResponse({'error': 'Video-only WebM or MP4 required'}, 415)
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > MAX_BYTES:
                return JSONResponse({'error': 'Video exceeds 16 MiB'}, 413)
        if not payload:
            return JSONResponse({'error': 'Empty video'}, 422)
        # Recheck after reading: concurrent uploads cannot both enter inference.
        if app.state.busy:
            return JSONResponse({'error': 'Another message is still processing'}, 429)
        for key, job in list(app.state.jobs.items()):
            if time.monotonic() - job['created'] > 600 and job['state'] != 'processing':
                del app.state.jobs[key]
        if len(app.state.jobs) >= 12:
            oldest = next((key for key, job in app.state.jobs.items() if job['state'] != 'processing'), None)
            if oldest:
                del app.state.jobs[oldest]
        job_id = str(uuid.uuid4())
        job = {'id': job_id, 'state': 'processing', 'phase': 'detecting', 'result': None,
               'created': time.monotonic(), 'cancelled': False}
        app.state.jobs[job_id] = job
        app.state.busy = True
        loop = asyncio.get_running_loop()

        def phase(value):
            if value in PHASES:
                loop.call_soon_threadsafe(job.update, {'phase': value})

        async def run():
            try:
                result = await asyncio.to_thread(app.state.backend.analyze, bytes(payload), mime, phase)
                if not job['cancelled']:
                    # No provider can accidentally promote an unreviewed output.
                    result = ExperimentResult.model_validate(result).model_dump(mode='json')
                    job.update(state='complete', result=result)
            except Exception:
                if not job['cancelled']:
                    job.update(state='failed', error='The message could not be interpreted. Please check framing and try again.')
            finally:
                payload.clear()
                app.state.busy = False

        task = asyncio.create_task(run())
        app.state.operations.add(task)
        task.add_done_callback(app.state.operations.discard)
        return JSONResponse({'id': job_id, 'state': 'processing'}, 202)

    @app.get('/jobs/{job_id}')
    def get_job(job_id: str):
        job = app.state.jobs.get(job_id)
        if not job or time.monotonic() - job['created'] > 600:
            return JSONResponse({'error': 'Message expired or unavailable'}, 404)
        return {key: value for key, value in job.items() if key not in {'created', 'cancelled'}}

    @app.delete('/jobs/{job_id}')
    def cancel_job(job_id: str):
        job = app.state.jobs.get(job_id)
        if job:
            job.update(cancelled=True, state='cancelled', result=None)
        return {'state': 'cancelled'}

    return app


app = create_app(web_port=int(os.getenv('NEOSIGNIS_WEB_PORT', '5173')))
