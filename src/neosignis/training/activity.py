"""Uncalibrated movement/visibility checks, not an ASL language detector."""
import re
import numpy as np

EVERYDAY = {
    'hello', 'hi', 'thank you', 'please', 'yes', 'no', 'i need help', 'i understand',
    'i do not understand', "i don't understand", 'please repeat that',
    'please sign more slowly', 'how are you', 'i am fine', "i'm fine",
}


def activity(features, timestamps_ms):
    raw = np.asarray(features).reshape(-1, 133, 3)
    times = np.asarray(timestamps_ms, dtype=float)
    if len(raw) < 3 or len(times) != len(raw) or not np.isfinite(raw).all() or not np.isfinite(times).all():
        raise ValueError('Invalid pose/timestamp sequence')
    if times[0] != 0 or np.any(np.diff(times) <= 0):
        raise ValueError('Timestamps must increase from zero')
    if times[-1] < 500:
        return {'usable': False, 'reason': 'too_short', 'segments': []}
    valid = raw[:, :, 2] > .3
    body = valid[:, [0, 3, 4, 5, 6, 7, 8, 9, 10]].sum(axis=1) >= 4
    hands = valid[:, 91:133].sum(axis=1) >= 8
    face = valid[:, 23:91].sum(axis=1) >= 6
    visibility = float(np.mean(body & hands & face))
    if visibility < .6:
        return {'usable': False, 'reason': 'framing', 'segments': [], 'visibility_fraction': visibility}
    center = (raw[:, 5, :2] + raw[:, 6, :2]) / 2
    width = np.linalg.norm(raw[:, 5, :2] - raw[:, 6, :2], axis=1)
    shoulders = valid[:, 5] & valid[:, 6] & (width > .01)
    relative = (raw[:, 91:133, :2] - center[:, None, :]) / np.maximum(width[:, None, None], .01)
    speeds = []
    for i, dt in enumerate(np.diff(times) / 1000, start=1):
        jointly_visible = valid[i, 91:133] & valid[i - 1, 91:133]
        if not shoulders[i] or not shoulders[i - 1] or jointly_visible.sum() < 6 or dt > .3:
            speeds.append(0.0)
        else:
            displacement = np.linalg.norm(relative[i] - relative[i - 1], axis=1)
            speeds.append(float(np.median(displacement[jointly_visible]) / dt))
    moving = np.asarray(speeds) > .25  # engineering heuristic; not calibrated ASL evidence
    active = [i for i in range(2, len(moving)) if moving[i - 2:i + 1].sum() >= 2]
    if not active or np.diff(times)[moving].sum() < 250:
        return {'usable': False, 'reason': 'no_clear_activity', 'segments': [], 'visibility_fraction': visibility}
    segments = [{'start_ms': max(0, int(times[active[0]]) - 200),
                 'end_ms': min(int(times[-1]), int(times[active[-1] + 1]) + 300)}]
    return {'usable': True, 'reason': 'possible_signing_activity', 'segments': segments,
            'visibility_fraction': visibility, 'detector': 'uncalibrated_motion_heuristic'}


def apply_output_policy(text, detection):
    """No calibrated semantic confidence exists: never return verified translation."""
    base = {'confidence': None, 'translated_text': None, 'candidate_text': None,
            'segments': detection.get('segments', []), 'quality_validated': False}
    if not detection['usable']:
        return base | {'disposition': 'abstained', 'reason': detection['reason']}
    cleaned = re.sub(r'\s+', ' ', str(text)).strip()
    normalized = re.sub(r"[^a-z' ]", '', cleaned.lower().replace('’', "'")).strip()
    if not cleaned or len(cleaned) > 512 or normalized not in EVERYDAY:
        return base | {'disposition': 'abstained', 'reason': 'outside_pilot_scope'}
    return base | {'disposition': 'needs_review', 'reason': 'uncalibrated_model', 'candidate_text': cleaned}
