"""Read-only integrity/structure checks for a bounded source TAR/ZIP, not ASL validation."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile
from zipfile import BadZipFile, ZipFile


def inspect_archive(path, *, expected_bytes=None, expected_sha256=None,
                    max_bytes=1_000_000_000, max_members=10_000):
    path = Path(path)
    size = path.stat().st_size
    if not 0 < size <= max_bytes:
        raise ValueError('Archive exceeds the configured size bound or is empty')
    if expected_bytes is not None and size != expected_bytes:
        raise ValueError('Archive size differs from the expected download size')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    actual_hash = digest.hexdigest()
    if expected_sha256 is not None and actual_hash != expected_sha256:
        raise ValueError('Archive SHA256 mismatch')

    seen, entries = set(), []
    total_bytes, count = 0, 0
    with tarfile.open(path, mode='r|') as archive:
        for member in archive:
            count += 1
            if count > max_members:
                raise ValueError('Archive exceeds the member-count limit')
            name = PurePosixPath(member.name)
            if (not member.name or name.is_absolute() or '..' in name.parts
                    or '\\' in member.name or (name.parts and ':' in name.parts[0])):
                raise ValueError('Archive contains an unsafe path')
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('Archive contains a link or special file')
            normalized = str(name)
            if normalized in seen:
                raise ValueError('Archive contains duplicate file paths')
            seen.add(normalized)
            if not 0 < member.size <= max_bytes:
                raise ValueError('Archive contains an empty or oversized file')
            total_bytes += member.size
            if total_bytes > max_bytes:
                raise ValueError('Archive contents exceed the configured size bound')
            file_digest = hashlib.sha256()
            read_bytes, prefix = 0, b''
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError('Archive file cannot be read')
            with stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    if not prefix:
                        prefix = chunk[:32]
                    read_bytes += len(chunk)
                    file_digest.update(chunk)
            if read_bytes != member.size:
                raise ValueError('Archive member is truncated')
            is_mp4 = name.suffix.lower() == '.mp4'
            entries.append({'path': normalized, 'bytes': read_bytes,
                            'sha256': file_digest.hexdigest(), 'is_mp4': is_mp4,
                            'mp4_ftyp_header': is_mp4 and prefix[4:8] == b'ftyp'})
    if not entries:
        raise ValueError('Archive has no regular files')
    return {
        'schema_version': 'neosignis.source-integrity.v1',
        'status': 'archive_structure_and_hashes_checked',
        'archive_bytes': size, 'archive_sha256': actual_hash,
        'files': len(entries), 'mp4_files': sum(e['is_mp4'] for e in entries),
        'mp4_files_with_ftyp': sum(e['mp4_ftyp_header'] for e in entries),
        'content_bytes': total_bytes, 'entries': entries,
        'video_decode_checked': False, 'linguistic_review_completed': False,
        'signer_split_verified': False, 'training_approved': False,
        'rendering_approved': False,
        'limitations': ['A computed hash is not a publisher-provided authenticity signature.',
                        'Container headers do not prove video decodability or signing quality.',
                        'No files were extracted, transformed, uploaded or used for training.'],
    }


def inspect_zip_archive(path, *, expected_bytes=None, expected_sha256=None,
                        max_bytes=1_000_000_000, max_content_bytes=4_000_000_000,
                        max_members=10_000):
    path = Path(path)
    size = path.stat().st_size
    if not 0 < size <= max_bytes:
        raise ValueError('Archive exceeds the configured size bound or is empty')
    if expected_bytes is not None and size != expected_bytes:
        raise ValueError('Archive size differs from the expected download size')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    actual_hash = digest.hexdigest()
    if expected_sha256 is not None and actual_hash != expected_sha256:
        raise ValueError('Archive SHA256 mismatch')
    entries, seen, content_bytes = [], set(), 0
    with ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise ValueError('Archive exceeds the member-count limit')
        for member in members:
            name = PurePosixPath(member.filename)
            if (not member.filename or name.is_absolute() or '..' in name.parts
                    or '\\' in member.filename or (name.parts and ':' in name.parts[0])):
                raise ValueError('Archive contains an unsafe path')
            if member.is_dir():
                continue
            mode = (member.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError('Archive contains a link or special file')
            if member.flag_bits & 1:
                raise ValueError('Encrypted archives need a separate reviewed process')
            normalized = str(name)
            if normalized in seen:
                raise ValueError('Archive contains duplicate file paths')
            seen.add(normalized)
            if not 0 < member.file_size <= max_content_bytes:
                raise ValueError('Archive contains an empty or oversized file')
            content_bytes += member.file_size
            if content_bytes > max_content_bytes:
                raise ValueError('Archive contents exceed the configured size bound')
            file_digest, prefix, read_bytes = hashlib.sha256(), b'', 0
            with archive.open(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    read_bytes += len(chunk)
                    if read_bytes > member.file_size:
                        raise ValueError('Archive member exceeds its declared size')
                    if not prefix:
                        prefix = chunk[:32]
                    file_digest.update(chunk)
            if read_bytes != member.file_size:
                raise ValueError('Archive member is truncated')
            is_mp4 = name.suffix.lower() == '.mp4'
            entries.append({'path': normalized, 'bytes': read_bytes,
                            'sha256': file_digest.hexdigest(), 'crc32': f'{member.CRC:08x}',
                            'is_mp4': is_mp4,
                            'mp4_ftyp_header': is_mp4 and prefix[4:8] == b'ftyp'})
    if not entries:
        raise ValueError('Archive has no regular files')
    return {
        'schema_version': 'neosignis.source-integrity.v1',
        'status': 'archive_structure_crc_and_hashes_checked', 'archive_format': 'zip',
        'archive_bytes': size, 'archive_sha256': actual_hash,
        'files': len(entries), 'mp4_files': sum(e['is_mp4'] for e in entries),
        'mp4_files_with_ftyp': sum(e['mp4_ftyp_header'] for e in entries),
        'content_bytes': content_bytes, 'entries': entries,
        'video_decode_checked': False, 'linguistic_review_completed': False,
        'signer_split_verified': False, 'training_approved': False,
        'rendering_approved': False,
        'limitations': ['ZIP CRC and computed hashes do not prove publisher authenticity.',
                        'Container headers do not prove video decodability or signing quality.',
                        'No files were extracted, transformed, uploaded or used for training.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--expected-bytes', type=int)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--max-bytes', type=int, default=1_000_000_000)
    parser.add_argument('--format', choices=('tar', 'zip'), default='tar')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.output.resolve() == args.archive.resolve():
            raise ValueError('Report output must not overwrite the source archive')
        inspect = inspect_zip_archive if args.format == 'zip' else inspect_archive
        result = inspect(args.archive, expected_bytes=args.expected_bytes,
                         expected_sha256=args.expected_sha256, max_bytes=args.max_bytes)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + '\n')
        summary = {key: value for key, value in result.items() if key != 'entries'}
        print(json.dumps(summary, indent=2))
        return 0
    except (OSError, ValueError, tarfile.TarError, BadZipFile) as exc:
        print(json.dumps({'status': 'archive_check_failed', 'message': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
