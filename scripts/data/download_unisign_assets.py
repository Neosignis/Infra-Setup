"""Acquire pinned local model assets; no training, inference or AWS access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

CODE_REVISION = 'eed438bcb49e30405cd6ccdfcccca330c134e830'
MODEL_REVISION = '64a2e24003b6e6bdbafca4f24c5f387921cdc6f0'
DECODER_REVISION = '2eb15465c5dd7f72a8f7984306ad05ebc3dd1e1f'
CHECKPOINT_SHA = '1bfd5f3312f04e4736f0a52f4ef9535916e6de9676a2a0d00c708748683fb00d'
CHECKPOINT_BYTES = 1186925007
SOURCE_FILES = ['models.py', 'datasets.py', 'deformable_attention_2d.py', 'stgcn_layers/__init__.py',
                'stgcn_layers/gcn_utils.py', 'stgcn_layers/stgcn_block.py']


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, destination, *, max_bytes, expected_sha=None, expected_bytes=None):
    """Resume byte ranges, verify known hashes, publish only complete files."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError('Refusing symlink destination')
    if destination.exists():
        size, digest = destination.stat().st_size, digest_file(destination)
        if size <= 0 or size > max_bytes or (expected_bytes is not None and size != expected_bytes) or (expected_sha and digest != expected_sha):
            raise ValueError(f'Existing asset differs from expected data: {destination.name}')
        return {'file': str(destination), 'bytes': size, 'sha256': digest, 'reused': True}
    partial = destination.with_name(destination.name + '.part')
    if partial.is_symlink():
        raise ValueError('Refusing symlink partial destination')
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > max_bytes:
        raise ValueError('Partial asset exceeds limit')
    if expected_bytes is None or offset != expected_bytes:
        request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
        with urllib.request.urlopen(request, timeout=45) as response:
            if offset and response.status == 206:
                if not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise ValueError('Server returned an inconsistent resume range')
            elif response.status == 200:
                offset = 0
            else:
                raise ValueError(f'Unexpected asset HTTP status {response.status}')
            with partial.open('ab' if offset else 'wb') as output:
                total, reported = offset, offset
                for chunk in iter(lambda: response.read(1024**2), b''):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError('Asset exceeds declared byte limit')
                    output.write(chunk)
                    if total - reported >= 64 * 1024**2:
                        print(json.dumps({'asset': destination.name, 'downloaded_bytes': total}), flush=True)
                        reported = total
    size, digest = partial.stat().st_size, digest_file(partial)
    if size <= 0 or (expected_bytes is not None and size != expected_bytes) or (expected_sha and digest != expected_sha):
        raise ValueError(f'Asset verification failed: {destination.name}')
    partial.replace(destination)
    return {'file': str(destination), 'bytes': size, 'sha256': digest, 'reused': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/local/models/unisign'))
    parser.add_argument('--skip-checkpoint', action='store_true')
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    if not args.skip_checkpoint and shutil.disk_usage(args.root).free < 4 * 1024**3:
        parser.error('At least 4 GiB free disk required for this local setup')
    receipt = {'code_revision': CODE_REVISION, 'model_revision': MODEL_REVISION,
               'decoder_revision': DECODER_REVISION, 'assets': [], 'training_run': False}
    for file in SOURCE_FILES:
        url = f'https://raw.githubusercontent.com/ZechengLi19/Uni-Sign/{CODE_REVISION}/{file}'
        receipt['assets'].append(download(url, args.root / 'source' / file, max_bytes=512 * 1024))
    for file in ['config.json', 'spiece.model', 'special_tokens_map.json', 'tokenizer_config.json']:
        url = f'https://huggingface.co/google/mt5-base/resolve/{DECODER_REVISION}/{file}'
        receipt['assets'].append(download(url, args.root / 'decoder' / file, max_bytes=8 * 1024**2))
    if not args.skip_checkpoint:
        file = 'how2sign_pose_only_slt.pth'
        url = f'https://huggingface.co/ZechengLi19/Uni-Sign/resolve/{MODEL_REVISION}/{file}'
        receipt['assets'].append(download(url, args.root / file, max_bytes=CHECKPOINT_BYTES,
                                          expected_bytes=CHECKPOINT_BYTES, expected_sha=CHECKPOINT_SHA))
    (args.root / 'acquisition.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'assets_acquired', 'assets': len(receipt['assets']),
                      'checkpoint_included': not args.skip_checkpoint}), flush=True)


if __name__ == '__main__':
    main()
