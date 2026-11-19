"""Cancellation must not reopen worker admission while a provider thread runs."""
import asyncio
import threading
import unittest

import httpx

from neosignis.worker import create_app
from test_contracts import utterance
from test_services import ProviderFixture


class AdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_caller_keeps_admission_until_provider_finishes(self):
        started, release = threading.Event(), threading.Event()
        provider = ProviderFixture()
        original = provider.recognize

        def blocking(request):
            started.set()
            if not release.wait(timeout=30):
                raise RuntimeError("test provider was not released")
            return original(request)

        provider.recognize = blocking
        app = create_app(provider)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture') as client:
                task = asyncio.create_task(client.post('/v1/recognize', json=utterance()))
                try:
                    # This checks cancellation/admission semantics, not startup
                    # latency. Busy developer machines may need extra startup time.
                    self.assertTrue(await asyncio.to_thread(started.wait, 10))
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                    self.assertTrue(app.state.busy)
                    self.assertEqual((await client.post('/v1/recognize', json=utterance())).status_code, 429)
                finally:
                    release.set()
                    await asyncio.gather(*app.state.operations)
                self.assertFalse(app.state.busy)
