import unittest

from pydantic import ValidationError

from neosignis.contracts import Capability, Frame, Point, RecognizeRequest, RecognizeResult, RenderResult


def utterance(language="ase"):
    return {"language": language, "feature_schema": "neosignis.landmarks.v1", "extractor_version": "test-only", "mirrored": False,
            "frames": [{"t_ms": t, "left_hand": [{"x": 0.1, "y": 0.2, "z": 0.0}] * 21} for t in (0, 33)]}


class ContractTests(unittest.TestCase):
    def test_missing_group_is_explicit(self):
        parsed = RecognizeRequest.model_validate(utterance())
        self.assertIsNone(parsed.frames[0].face)

    def test_exact_group_size(self):
        payload = utterance()
        payload["frames"][0]["left_hand"].pop()
        with self.assertRaises(ValidationError):
            RecognizeRequest.model_validate(payload)

    def test_time_order_and_origin(self):
        for timestamps in ([0, 0], [0, -1], [1, 33], [0, 10001]):
            payload = utterance()
            for frame, timestamp in zip(payload["frames"], timestamps):
                frame["t_ms"] = timestamp
            with self.subTest(timestamps=timestamps), self.assertRaises(ValidationError):
                RecognizeRequest.model_validate(payload)

    def test_nonfinite_point_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValidationError):
                Point(x=value, y=0, z=0)

    def test_empty_frame_rejected(self):
        with self.assertRaises(ValidationError):
            Frame(t_ms=0)

    def test_unknown_language_rejected(self):
        with self.assertRaises(ValidationError):
            RecognizeRequest.model_validate(utterance("unknown"))

    def test_no_uncalibrated_confidence(self):
        with self.assertRaises(ValidationError):
            RecognizeResult(language="ase", status="final", text="fixture", model_version="fixture", confidence=0.99)

    def test_abstention_cannot_contain_translation(self):
        with self.assertRaises(ValidationError):
            RecognizeResult(language="ase", status="abstained", text="fixture", model_version="fixture", reason="uncertain")

    def test_render_ready_needs_asset(self):
        with self.assertRaises(ValidationError):
            RenderResult(language="ase", signer_id="fixture", renderer_version="fixture", status="ready")

    def test_capability_cannot_enable_without_approval(self):
        with self.assertRaises(ValidationError):
            Capability(language="ase", recognize=True)
