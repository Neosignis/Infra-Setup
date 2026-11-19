"""Frame/pose diagnostics and honest source-versus-overlay review media."""
from fractions import Fraction
from pathlib import Path

import numpy as np

PART_JOINTS = {'body': [0, 3, 4, 5, 6, 7, 8, 9, 10], 'left_hand': list(range(91, 112)),
               'right_hand': list(range(112, 133)), 'face': list(range(23, 91))}
HAND_EDGES = [(0, finger) for finger in (1, 5, 9, 13, 17)] + [
    (finger + offset, finger + offset + 1) for finger in (1, 5, 9, 13, 17) for offset in range(3)]


def inspect_video(path, *, max_frames=7200):
    import av
    path = Path(path)
    if not 0 < path.stat().st_size <= 8 * 1024**2:
        raise ValueError('Source clip exceeds bounded review size')
    stamps, dimensions = [], None
    with av.open(path, format='mov', options={'enable_drefs': '0'}) as container:
        if len(container.streams.video) != 1:
            raise ValueError('Expected exactly one source video stream')
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        rate = stream.average_rate
        source_time_base = str(stream.time_base)
        for count, frame in enumerate(container.decode(video=0), 1):
            if count > max_frames or not (0 < frame.width <= 1920 and 0 < frame.height <= 1080):
                raise ValueError('Source video exceeds review decode bounds')
            if dimensions is not None and dimensions != (frame.width, frame.height):
                raise ValueError('Changing frame dimensions')
            dimensions = frame.width, frame.height
            if frame.pts is None or frame.time_base is None:
                raise ValueError('Source frame lacks PTS')
            stamp = frame.pts * frame.time_base
            if stamps and stamp <= stamps[-1]:
                raise ValueError('Source timestamps do not increase')
            stamps.append(stamp)
        audio = len(container.streams.audio)
        rotation = stream.metadata.get('rotate')
    if len(stamps) < 2 or rate is None:
        raise ValueError('Insufficient source timing metadata')
    origin = stamps[0]
    relative = [float((stamp - origin) * 1000) for stamp in stamps]
    return {'frames': len(stamps), 'width': dimensions[0], 'height': dimensions[1],
            'timestamps_ms': relative, 'last_pts_ms': relative[-1], 'fps_metadata': str(rate),
            'time_base': source_time_base,
            'audio_streams': audio, 'rotation_tag': rotation}


def compare_poses(stored, fresh, width, height):
    """Disagreement with another extractor, NOT error against human ground truth."""
    a, b = np.asarray(stored).reshape(133, 3), np.asarray(fresh).reshape(133, 3)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Nonfinite diagnostic pose')
    valid = (a[:, 2] > .3) & (b[:, 2] > .3)
    distances = np.linalg.norm((a[:, :2] - b[:, :2]) * [width, height], axis=1) / np.hypot(width, height)
    result = {}
    for part, indices in PART_JOINTS.items():
        values = distances[indices][valid[indices]]
        result[part] = {'jointly_visible': int(len(values)),
                        'median_distance_image_diagonal': float(np.median(values)) if len(values) else None,
                        'p95_distance_image_diagonal': float(np.quantile(values, .95)) if len(values) else None}
    return result


def draw_pose(image, features):
    import cv2
    output = image.copy()
    raw = np.asarray(features).reshape(133, 3)
    height, width = output.shape[:2]
    points = np.rint(raw[:, :2] * [width, height]).astype(np.int32)
    valid = (raw[:, 2] > .3) & (points[:, 0] >= 0) & (points[:, 0] < width) & (points[:, 1] >= 0) & (points[:, 1] < height)
    colors = {'body': (40, 225, 225), 'left_hand': (80, 240, 80), 'right_hand': (40, 140, 255), 'face': (235, 100, 220)}
    for name, joints in PART_JOINTS.items():
        color = colors[name]
        for joint in joints:
            if valid[joint]: cv2.circle(output, tuple(points[joint]), 1 if name == 'face' else 2, color, -1, cv2.LINE_AA)
        if 'hand' in name:
            offset = joints[0]
            for a, b in HAND_EDGES:
                if valid[offset + a] and valid[offset + b]:
                    cv2.line(output, tuple(points[offset + a]), tuple(points[offset + b]), color, 1, cv2.LINE_AA)
    for a, b in [(5, 6), (5, 7), (7, 9), (6, 8), (8, 10)]:
        if valid[a] and valid[b]: cv2.line(output, tuple(points[a]), tuple(points[b]), colors['body'], 1, cv2.LINE_AA)
    return output


def make_review_video(source_path, sample, output_path, *, extractor=None):
    import av
    import cv2
    sample.validate()
    source_path, output_path = Path(source_path), Path(output_path)
    if source_path.resolve() == output_path.resolve() or output_path.exists():
        raise ValueError('Use a new derived output; preserve the original video')
    info = inspect_video(source_path)
    lookup = {int(frame): index for index, frame in enumerate(sample.frame_indices)}
    sampled = sorted(set(np.linspace(0, info['frames'] - 1, 5).round().astype(int).tolist()))
    checks = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h, banner = info['width'], info['height'], 48
    encoded_height = (h + banner + 1) // 2 * 2
    clock = Fraction(1, 90000)
    last_frame = None
    with av.open(source_path, format='mov') as original, av.open(output_path, 'w') as target:
        stream = target.add_stream('libx264', rate=Fraction(info['fps_metadata']))
        stream.width, stream.height, stream.pix_fmt = w * 2, encoded_height, 'yuv420p'
        stream.time_base = clock; stream.codec_context.time_base = clock
        stream.options = {'crf': '20', 'preset': 'fast', 'tune': 'zerolatency'}
        for index, frame in enumerate(original.decode(video=0)):
            image = frame.to_ndarray(format='bgr24')
            stored = sample.features[lookup[index]] if index in lookup else None
            overlay = draw_pose(image, stored) if stored is not None else image.copy()
            composed = np.zeros((encoded_height, w * 2, 3), dtype=np.uint8)
            composed[banner:banner + h, :w], composed[banner:banner + h, w:] = image, overlay
            cv2.putText(composed, 'SOURCE', (8, 17), cv2.FONT_HERSHEY_SIMPLEX, .42, (240, 240, 240), 1, cv2.LINE_AA)
            cv2.putText(composed, 'STORED POSE / INDEX CANDIDATE', (w + 6, 17), cv2.FONT_HERSHEY_SIMPLEX, .32, (150, 240, 160), 1, cv2.LINE_AA)
            label = f'Frame {index} | PTS {info["timestamps_ms"][index]:.1f} ms | meaning review pending'
            cv2.putText(composed, label, (8, 37), cv2.FONT_HERSHEY_SIMPLEX, .32, (220, 220, 220), 1, cv2.LINE_AA)
            if stored is None:
                cv2.putText(composed, 'NO CORRESPONDING STORED POSE', (w + 8, banner + 30), cv2.FONT_HERSHEY_SIMPLEX, .35, (70, 80, 255), 1)
            if index in sampled and stored is not None and extractor is not None:
                try:
                    fresh, _ = extractor(frame)
                    checks.append({'frame_index': index, 'pts_ms': info['timestamps_ms'][index],
                                   'comparison': compare_poses(stored, fresh, w, h)})
                except ValueError:
                    checks.append({'frame_index': index, 'pts_ms': info['timestamps_ms'][index],
                                   'comparison_unavailable': True})
            if index == info['frames'] // 2:
                last_frame = composed.copy()
            derived = av.VideoFrame.from_ndarray(composed, format='bgr24')
            derived.pts = round(info['timestamps_ms'][index] * 90)
            derived.time_base = clock
            for packet in stream.encode(derived): target.mux(packet)
        for packet in stream.encode(): target.mux(packet)
    derived = inspect_video(output_path)
    if derived['frames'] != info['frames'] or not np.allclose(derived['timestamps_ms'], info['timestamps_ms'], atol=.1, rtol=0):
        raise ValueError('Derived review video did not preserve source frame count/timing')
    thumb = output_path.with_suffix('.jpg')
    if last_frame is not None: cv2.imwrite(str(thumb), last_frame)
    medians = [part['median_distance_image_diagonal'] for check in checks if 'comparison' in check
               for part in check['comparison'].values() if part['median_distance_image_diagonal'] is not None]
    flags = []
    if len(sample.features) != info['frames']: flags.append('source_pose_frame_count_differs')
    if set(lookup) != set(range(info['frames'])): flags.append('stored_indices_do_not_cover_source_exactly')
    if info['rotation_tag'] not in (None, '0'): flags.append('source_rotation_requires_review')
    if checks and not medians: flags.append('fresh_pose_comparison_unavailable')
    if any(value > .08 for value in medians): flags.append('sampled_spatial_disagreement_review_needed')
    return {key: value for key, value in info.items() if key != 'timestamps_ms'} | {
        'pose_frames': len(sample.features), 'pose_frame_count_matches': len(sample.features) == info['frames'],
        'source_indices_cover_video_exactly': set(lookup) == set(range(info['frames'])),
        'derived_frame_count_and_pts_checked': True, 'pose_timestamps_known': False,
        'sampled_current_extractor_comparisons': checks, 'engineering_review_flags': flags,
        'spatial_threshold_is_uncalibrated': True, 'linguistic_review_completed': False,
        'video_pose_alignment_approved': False, 'review_video': str(output_path), 'thumbnail': str(thumb)}
