"""Validate a local capture ZIP without extracting or uploading its recordings."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from zipfile import BadZipFile, ZipFile

MAX_BYTES = 64 * 1024 * 1024
MAX_CLIP_BYTES = 8 * 1024 * 1024
LABELS = {f'E{i:02}' for i in range(1, 13)}


def validate_archive(path):
    with ZipFile(path) as archive:
        entries = archive.infolist()
        names = [info.filename for info in entries]
        if len(names) != len(set(names)):
            raise ValueError('Archive has duplicate paths')
        if any(PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name for name in names):
            raise ValueError('Archive contains an unsafe path')
        if sum(info.file_size for info in entries) > MAX_BYTES + 1024 * 1024:
            raise ValueError('Uncompressed archive exceeds the capture-session limit')
        if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 1024 * 1024:
            raise ValueError('Archive needs a bounded manifest.json')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('schema_version') != 'neosignis.capture.v1' or manifest.get('language') != 'ase':
            raise ValueError('Unsupported manifest schema or language')
        if manifest.get('training_authorized') is not False or manifest.get('rendering_authorized') is not False:
            raise ValueError('Local capture cannot assert training or rendering authorization')
        clips = manifest.get('clips')
        if not isinstance(clips, list) or not 1 <= len(clips) <= 12:
            raise ValueError('A capture session needs 1-12 clips')
        ids, hashes, signers, files = set(), set(), set(), set()
        for clip in clips:
            clip_id, signer, reference = (clip.get(key) for key in ('id', 'signer_id', 'permission_reference'))
            if not isinstance(clip_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', clip_id) or clip_id in ids:
                raise ValueError('Clip IDs must be valid and unique')
            ids.add(clip_id)
            if not isinstance(signer, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', signer):
                raise ValueError('A pseudonymous signer code is required')
            if not isinstance(reference, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', reference):
                raise ValueError('A recording permission reference is required')
            if clip.get('local_recording_acknowledged') is not True or clip.get('rights_review_status') != 'unreviewed':
                raise ValueError('Local recording acknowledgement and pending rights review are required')
            if clip.get('split') != 'unassigned':
                raise ValueError('Dataset splits need separate signer-aware assignment')
            expected = clip.get('expected_intent')
            if expected is not None and (not isinstance(expected, str) or expected not in LABELS):
                raise ValueError('Unknown meaning label')
            duration = clip.get('duration_ms')
            if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 100 <= duration <= 10_000:
                raise ValueError('Clip duration must be between 100 ms and 10 seconds')
            file_name = clip.get('file')
            if not isinstance(file_name, str) or not re.fullmatch(r'clips/[A-Za-z0-9_-]+\.(webm|mp4)', file_name) or file_name not in names or file_name in files:
                raise ValueError('Each clip needs a unique local video file')
            files.add(file_name)
            info = archive.getinfo(file_name)
            if not 1 <= info.file_size <= MAX_CLIP_BYTES or clip.get('bytes') != info.file_size:
                raise ValueError('Clip size does not match its manifest or exceeds the limit')
            digest = hashlib.sha256(archive.read(file_name)).hexdigest()
            if clip.get('sha256') != digest:
                raise ValueError('Clip checksum mismatch')
            if digest in hashes:
                raise ValueError('Duplicate recordings need review before ingestion')
            hashes.add(digest)
            signers.add(signer)
        unexpected = set(names) - files - {'manifest.json', 'README.txt', 'clips/'}
        if unexpected:
            raise ValueError('Archive contains files outside its recording manifest')
        return {'status': 'capture_integrity_passed', 'clips': len(clips), 'signers': len(signers), 'training_ready': False, 'review_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_archive(args.archive), indent=2))
        return 0
    except (BadZipFile, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({'status': 'invalid_capture', 'message': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
