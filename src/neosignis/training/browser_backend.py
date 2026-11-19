"""Whole-message local camera experiment; does not persist videos or train."""
import io
from pathlib import Path
import time

import numpy as np

from .activity import activity, apply_output_policy
from .pose import POSE_SCHEMA, load_local_pose_extractor, torch_unisign_collate
from .utterances import Utterance

MAX_VIDEO_BYTES = 16 * 1024**2


def extract_video(payload, mime, extractor, progress=lambda phase: None):
    import av
    if not 0 < len(payload) <= MAX_VIDEO_BYTES:
        raise ValueError('Invalid video size')
    container_format = {'video/webm': 'matroska', 'video/mp4': 'mov'}.get(mime)
    if not container_format:
        raise ValueError('Unsupported video format')
    features, masks, times, origin, previous = [], [], [], None, None
    with av.open(io.BytesIO(payload), format=container_format, options={'enable_drefs': '0'}) as container:
        if len(container.streams.video) != 1 or len(container.streams.audio):
            raise ValueError('Expected one video stream without audio')
        container.streams.video[0].codec_context.thread_count = 1
        dimensions = None
        for count, frame in enumerate(container.decode(video=0), start=1):
            if count > 1800 or not (0 < frame.width <= 1920 and 0 < frame.height <= 1080):
                raise ValueError('Video exceeds local decode bounds')
            if dimensions is not None and dimensions != (frame.width, frame.height):
                raise ValueError('Frame dimensions changed')
            dimensions = (frame.width, frame.height)
            if frame.time is None or not np.isfinite(frame.time):
                raise ValueError('Missing video timestamp')
            stamp = float(frame.time)
            if previous is not None and stamp <= previous:
                raise ValueError('Video timestamps do not increase')
            origin = stamp if origin is None else origin
            if stamp - origin > 30:
                raise ValueError('Video exceeds 30-second local bound')
            previous = stamp
            values, observed = extractor(frame)
            features.append(values); masks.append(observed); times.append((stamp - origin) * 1000)
            if count % 24 == 0:
                progress('detecting')
    if len(features) < 3:
        raise ValueError('Video too short')
    if times[-1] >= 29500:
        return None  # recorder deadline may have cut an utterance
    return Utterance('local-message', 'Unlabelled camera message.', 'val', np.stack(features),
                     np.stack(masks), np.asarray(times), POSE_SCHEMA, 'rtmlib.0.0.13.raw-simcc-v1').validate()


class BrowserBackend:
    def __init__(self, root):
        self.root = Path(root)
        self.extractor, self.model = None, None

    def available(self):
        return all((self.root / file).is_file() for file in
                   ['acquisition.json', 'how2sign_pose_only_slt.pth', 'pose/assets.json'])

    def analyze(self, payload, mime, progress):
        import torch
        from .unisign_runtime import load_unisign, translate
        torch.set_num_threads(2)
        started = time.monotonic()
        if self.extractor is None:
            progress('loading_pose')
            self.extractor = load_local_pose_extractor(self.root)
        progress('detecting')
        sample = extract_video(payload, mime, self.extractor, progress)
        if sample is None:
            detection = {'usable': False, 'reason': 'unfinished_message', 'segments': []}
        else:
            detection = activity(sample.features, sample.timestamps_ms)
        if not detection['usable']:
            return apply_output_policy('', detection) | {'elapsed_s': round(time.monotonic() - started, 2)}
        if self.model is None:
            progress('loading_model')
            self.model = load_unisign(self.root, device='cpu')
        progress('translating')
        source, _ = torch_unisign_collate([sample])
        prediction = translate(self.model, source, max_new_tokens=40)[0]
        return apply_output_policy(prediction, detection) | {'elapsed_s': round(time.monotonic() - started, 2)}
