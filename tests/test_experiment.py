import io
import threading
import time
import unittest

import numpy as np
from fastapi.testclient import TestClient

from neosignis.experiment import create_app, MAX_BYTES
from neosignis.training.activity import activity, apply_output_policy
from neosignis.training.browser_backend import extract_video

HEADERS = {'X-Neosignis-Request': '1', 'Origin': 'http://127.0.0.1:5173'}


def pose_sequence(moving=True):
    raw = np.full((40, 133, 3), .5, dtype=np.float32)
    raw[:, :, 2] = .9
    raw[:, 5, 0], raw[:, 6, 0] = .3, .7
    if moving:
        raw[:, 91:133, 0] += (.08 * np.sin(np.linspace(0, 4 * np.pi, 40)))[:, None]
    return raw.reshape(40, 399), np.arange(40) * 40


class ActivityTests(unittest.TestCase):
    def test_possible_signing_has_bounded_candidate_boundaries(self):
        features, times = pose_sequence()
        detected = activity(features, times)
        self.assertTrue(detected['usable'])
        self.assertGreaterEqual(detected['segments'][0]['start_ms'], 0)
        self.assertLessEqual(detected['segments'][-1]['end_ms'], times[-1])
        self.assertEqual(detected['detector'], 'uncalibrated_motion_heuristic')

    def test_still_hands_and_missing_signer_abstain(self):
        features, times = pose_sequence(False)
        self.assertEqual(activity(features, times)['reason'], 'no_clear_activity')
        self.assertEqual(activity(np.zeros_like(features), times)['reason'], 'framing')

    def test_camera_or_torso_translation_alone_is_not_hand_activity(self):
        features, times = pose_sequence(False)
        raw = features.reshape(-1, 133, 3)
        raw[:, :, 0] += np.linspace(0, .2, len(raw))[:, None]
        self.assertFalse(activity(features, times)['usable'])

    def test_static_hands_are_not_claimed_to_be_non_asl(self):
        features, times = pose_sequence(False)
        detected = activity(features, times)
        result = apply_output_policy('Hello.', detected)
        self.assertEqual(result['disposition'], 'abstained')
        self.assertIsNone(result['confidence'])
        self.assertIsNone(result['translated_text'])

    def test_raw_prediction_never_promoted_to_verified_translation(self):
        detection = activity(*pose_sequence())
        result = apply_output_policy('Hello.', detection)
        self.assertEqual(result['disposition'], 'needs_review')
        self.assertEqual(result['candidate_text'], 'Hello.')
        self.assertIsNone(result['translated_text'])
        self.assertIsNone(result['confidence'])
        self.assertFalse(result['quality_validated'])

    def test_outside_scope_prediction_is_withheld(self):
        result = apply_output_policy('Draw your shoulders and relax.', activity(*pose_sequence()))
        self.assertEqual(result['reason'], 'outside_pilot_scope')
        self.assertIsNone(result['candidate_text'])

    def test_short_and_invalid_timestamp_sequences(self):
        features, times = pose_sequence()
        self.assertEqual(activity(features[:4], times[:4])['reason'], 'too_short')
        times[1] = times[0]
        with self.assertRaises(ValueError):
            activity(features, times)


class FakeBackend:
    def __init__(self):
        self.entered, self.release = threading.Event(), threading.Event()
        self.release.set()
        self.calls = []
        self.promote = False

    def available(self):
        return True

    def analyze(self, payload, mime, phase):
        self.calls.append((payload, mime))
        phase('translating')
        self.entered.set()
        self.release.wait(10)
        result = apply_output_policy('Hello.', {'usable': True, 'segments': []})
        if self.promote:
            result['translated_text'] = 'Hello.'
        return result


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.app = create_app(self.backend)
        self.client = TestClient(self.app, base_url='http://127.0.0.1')
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def submit(self, payload=b'video-test-fixture', mime='video/webm'):
        return self.client.post('/jobs', content=payload, headers=HEADERS | {'Content-Type': mime})

    def completed(self, job_id):
        for _ in range(100):
            job = self.client.get('/jobs/' + job_id, headers=HEADERS).json()
            if job['state'] != 'processing':
                return job
            time.sleep(.01)
        self.fail('Job did not complete')

    def test_status_distinguishes_experiment_from_approved_model(self):
        data = self.client.get('/status', headers=HEADERS).json()
        self.assertTrue(data['available'])
        self.assertFalse(data['quality_validated'])
        self.assertFalse(data['confidence_calibrated'])

    def test_origin_header_and_host_guard(self):
        self.assertEqual(self.client.get('/status').status_code, 403)
        self.assertEqual(self.client.get('/status', headers=HEADERS | {'Origin': 'https://untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.get('/status', headers=HEADERS | {'Host': 'untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.options('/jobs', headers={'Origin': 'https://untrusted.example'}).status_code, 403)

    def test_raw_video_job_has_no_meaning_or_label_input(self):
        response = self.submit()
        self.assertEqual(response.status_code, 202)
        job = self.completed(response.json()['id'])
        self.assertEqual(job['state'], 'complete')
        self.assertEqual(job['result']['disposition'], 'needs_review')
        self.assertEqual(self.backend.calls, [(b'video-test-fixture', 'video/webm')])
        self.assertNotIn('created', job)

    def test_json_labels_empty_and_oversized_bodies_rejected(self):
        self.assertEqual(self.submit(b'{"meaning":"hello"}', 'application/json').status_code, 415)
        self.assertEqual(self.submit(b'').status_code, 422)
        self.assertEqual(self.submit(b'x' * (MAX_BYTES + 1)).status_code, 413)
        self.assertFalse(self.backend.calls)

    def test_cancel_does_not_release_running_model_admission(self):
        self.backend.release.clear()
        try:
            job_id = self.submit().json()['id']
            self.assertTrue(self.backend.entered.wait(2))
            self.client.delete('/jobs/' + job_id, headers=HEADERS)
            self.assertEqual(self.submit().status_code, 429)
            self.assertTrue(self.client.get('/status', headers=HEADERS).json()['busy'])
        finally:
            self.backend.release.set()
        self.assertEqual(self.completed(job_id)['state'], 'cancelled')

    def test_provider_cannot_claim_verified_translation(self):
        self.backend.promote = True
        job_id = self.submit().json()['id']
        job = self.completed(job_id)
        self.assertEqual(job['state'], 'failed')
        self.assertIsNone(job['result'])


class BrowserDecodeTests(unittest.TestCase):
    def test_real_webm_decodes_fully_with_preserved_timestamps(self):
        import av
        payload = io.BytesIO()
        with av.open(payload, 'w', format='webm') as container:
            stream = container.add_stream('libvpx', rate=10)
            stream.width, stream.height, stream.pix_fmt = 32, 32, 'yuv420p'
            for _ in range(12):
                frame = av.VideoFrame(32, 32, 'rgb24')
                frame.planes[0].update(bytes(frame.planes[0].buffer_size))
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        extractor = lambda frame: (np.zeros(399, dtype=np.float32), np.zeros(399, dtype=np.bool_))
        result = extract_video(payload.getvalue(), 'video/webm', extractor)
        self.assertEqual(len(result.features), 12)
        self.assertAlmostEqual(result.timestamps_ms[-1], 1100)

    def test_nonvideo_and_bad_mime_rejected(self):
        with self.assertRaises(Exception):
            extract_video(b'not a container', 'video/webm', lambda frame: None)
        with self.assertRaises(ValueError):
            extract_video(b'not a container', 'application/json', lambda frame: None)


if __name__ == '__main__':
    unittest.main()
