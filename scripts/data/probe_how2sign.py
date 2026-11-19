"""Bounded, local video-decode diagnostics; no training or linguistic evaluation."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import sys
import time
from zipfile import ZipFile


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def select_names(references, available, count):
    if not 1 <= count <= 64:
        raise ValueError('Select between 1 and 64 clips for this bounded probe')
    candidates = sorted(set(references) & set(available))
    if not candidates:
        raise ValueError('No matching video/reference IDs')
    durations = {}
    for name in candidates:
        duration = float(references[name]['END']) - float(references[name]['START'])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('Reference duration must be positive and finite')
        durations[name] = duration
    ordered = sorted(candidates, key=lambda name: (durations[name], name))
    selected = []
    # Include duration extremes, then a stable hash-based sample across IDs.
    for name in [ordered[0], ordered[-1]] + sorted(candidates, key=lambda n: hashlib.sha256(n.encode()).hexdigest()):
        if name not in selected:
            selected.append(name)
        if len(selected) == min(count, len(candidates)):
            break
    return selected


def decode_video_bytes(payload, *, max_bytes=32 * 1024 * 1024, max_frames=3000):
    import av
    if not payload or len(payload) > max_bytes:
        raise ValueError('Video bytes exceed the bounded probe limit or are empty')
    if max_frames < 1:
        raise ValueError('Frame limit must be positive')
    started = time.monotonic()
    # Force local MP4/MOV parsing and disable external data references.
    with av.open(io.BytesIO(payload), format='mov', options={'enable_drefs': '0'}) as container:
        if len(container.streams.video) != 1:
            raise ValueError('Expected exactly one video stream')
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        width, height = stream.codec_context.width, stream.codec_context.height
        if not (0 < width <= 4096 and 0 < height <= 4096):
            raise ValueError('Unsupported source dimensions for this bounded probe')
        rate = float(stream.average_rate) if stream.average_rate else None
        timestamps, missing, count, rgb_checked = [], 0, 0, False
        for frame in container.decode(video=0):
            count += 1
            if count > max_frames:
                raise ValueError('Frame limit exceeded; full decode was not completed')
            if frame.width != width or frame.height != height:
                raise ValueError('Frame dimensions changed during the clip')
            if not rgb_checked:
                rgb = frame.reformat(format='rgb24')
                rgb_checked = rgb.format.name == 'rgb24' and rgb.width == width and rgb.height == height
            if frame.time is None:
                missing += 1
            else:
                timestamp = float(frame.time)
                if not math.isfinite(timestamp):
                    raise ValueError('Non-finite frame timestamp')
                timestamps.append(timestamp)
        if count == 0:
            raise ValueError('Video decoded no frames')
        steps = [b - a for a, b in zip(timestamps, timestamps[1:])]
        violations = sum(step <= 0 for step in steps)
        span_ms = (timestamps[-1] - timestamps[0]) * 1000 if len(timestamps) >= 2 else None
        container_ms = container.duration / 1000 if container.duration is not None else None
        return {
            'full_clip_decode_completed': True, 'codec': stream.codec_context.name,
            'width': width, 'height': height, 'fps_metadata': rate,
            'decoded_frames': count, 'timestamp_span_ms': span_ms,
            'container_duration_ms': container_ms,
            'frame_interval_median_ms': statistics.median(steps) * 1000 if steps else None,
            'missing_timestamps': missing, 'nonincreasing_timestamps': violations,
            'first_frame_rgb24_conversion_checked': rgb_checked,
            'decode_elapsed_ms': round((time.monotonic() - started) * 1000, 2),
        }


def probe_dataset(archive_path, inventory_path, references_path, *, sample_size=32):
    import av
    inventory = json.loads(Path(inventory_path).read_text())
    if file_hash(archive_path) != inventory['archive_sha256']:
        raise ValueError('Source archive changed since integrity inspection')
    with Path(references_path).open(newline='', encoding='utf-8-sig') as source:
        rows = list(csv.DictReader(source, delimiter='\t'))
    references = {row['SENTENCE_NAME']: row for row in rows}
    if len(references) != len(rows):
        raise ValueError('Duplicate reference IDs require review')
    videos = {PurePosixPath(e['path']).stem: e for e in inventory['entries'] if e['is_mp4']}
    if len(videos) != inventory['mp4_files']:
        raise ValueError('Duplicate video IDs require review')
    selected = select_names(references, videos, sample_size)
    if sum(videos[name]['bytes'] for name in selected) > 512 * 1024 * 1024:
        raise ValueError('Selected sample exceeds total read budget')
    results = []
    with ZipFile(archive_path) as archive:
        for name in selected:
            entry = videos[name]
            row = {'id': name, 'reference_duration_ms': (float(references[name]['END']) - float(references[name]['START'])) * 1000}
            try:
                member = archive.getinfo(entry['path'])
                if not 0 < member.file_size <= 32 * 1024 * 1024:
                    raise ValueError('Clip exceeds per-video byte bound')
                payload = archive.read(member)
                if len(payload) != entry['bytes'] or hashlib.sha256(payload).hexdigest() != entry['sha256']:
                    raise ValueError('Clip differs from the checked inventory')
                row.update(decode_video_bytes(payload))
                row['status'] = 'decoded'
            except Exception as exc:
                row.update({'status': 'failed', 'full_clip_decode_completed': False,
                            'error_type': type(exc).__name__, 'error': str(exc)[:500]})
            results.append(row)
    decoded = [r for r in results if r['status'] == 'decoded']
    all_durations = [(float(references[n]['END']) - float(references[n]['START'])) * 1000 for n in set(references) & set(videos)]
    return {
        'schema_version': 'neosignis.video-probe.v1',
        'status': 'sampled_decode_checked' if len(decoded) == len(selected) else 'sampled_decode_has_failures',
        'decoder': {'name': 'PyAV', 'version': av.__version__},
        'archive_sha256': inventory['archive_sha256'], 'references_sha256': file_hash(references_path),
        'source_split': 'publisher_validation', 'source_video_count': len(videos),
        'sample_method': 'shortest and longest reference durations plus deterministic hash sample',
        'sampled_clips': len(selected), 'fully_decoded_clips': len(decoded),
        'failed_clips': len(selected) - len(decoded),
        'sample_dimensions': sorted({f"{r['width']}x{r['height']}" for r in decoded}),
        'sample_fps_metadata': sorted({r['fps_metadata'] for r in decoded if r['fps_metadata'] is not None}),
        'sample_timestamp_issue_clips': sum(bool(r['missing_timestamps'] or r['nonincreasing_timestamps']) for r in decoded),
        'matched_reference_duration_ms_range': [min(all_durations), max(all_durations)],
        'matched_reference_utterances_over_10_seconds': sum(d > 10000 for d in all_durations),
        'results': results, 'all_source_videos_decoded': len(decoded) == len(videos),
        'linguistic_review_completed': False, 'training_approved': False,
        'notes': ['No training, feature extraction, cropping or saved-frame dataset was produced.',
                  'Filename matches and plausible duration do not establish temporal/semantic alignment.',
                  'Decode timing is not interpretation latency or a model benchmark.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--references', required=True, type=Path)
    parser.add_argument('--sample-size', type=int, default=32)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.output.resolve() in {p.resolve() for p in (args.archive, args.inventory, args.references)}:
            raise ValueError('Output must not overwrite a source input')
        result = probe_dataset(args.archive, args.inventory, args.references, sample_size=args.sample_size)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'results'}, indent=2))
        return 0 if result['failed_clips'] == 0 else 1
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(json.dumps({'status': 'probe_failed', 'message': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
