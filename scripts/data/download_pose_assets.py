"""Download the upstream lightweight detector/whole-body ONNX assets locally."""
import json
from pathlib import Path
from zipfile import ZipFile
import hashlib
import shutil
import argparse
import urllib.request

from download_unisign_assets import download

ASSETS = {
    'detector': 'rtmposev1/onnx_sdk/yolox_tiny_8xb8-300e_humanart-6f3252f9.zip',
    'pose': 'rtmw/onnx_sdk/rtmw-dw-l-m_simcc-cocktail14_270e-256x192_20231122.zip',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mirror', action='store_true', help='Use the extractor maintainer\'s public Hugging Face mirror')
    args = parser.parse_args()
    root = Path('data/local/models/unisign/pose').resolve()
    root.mkdir(parents=True, exist_ok=True)
    base = 'https://download.openmmlab.com/mmpose/v1/projects/'
    if args.mirror:
        with urllib.request.urlopen('https://huggingface.co/api/models/Tau-J/RTMPose', timeout=30) as response:
            revision = json.load(response)['sha']
        base = f'https://huggingface.co/Tau-J/RTMPose/resolve/{revision}/'
    receipts = {}
    for name, remote in ASSETS.items():
        url = base + remote
        archive_path = root / (name + ('.mirror.zip' if args.mirror else '.zip'))
        receipt = download(url, archive_path, max_bytes=256 * 1024**2)
        output = root / (name + '.onnx')
        if not output.exists():
            with ZipFile(archive_path) as archive:
                candidates = [entry for entry in archive.infolist() if entry.filename.endswith('end2end.onnx')]
                if len(candidates) != 1 or not 0 < candidates[0].file_size <= 256 * 1024**2:
                    raise ValueError('Expected one bounded ONNX model')
                # Write a fixed local name; do not extract archive paths.
                partial = output.with_suffix('.onnx.part')
                with archive.open(candidates[0]) as source, partial.open('wb') as target:
                    shutil.copyfileobj(source, target, 1024**2)
                partial.replace(output)
        receipts[name] = {'url': url, 'archive': receipt, 'onnx': str(output),
                          'onnx_bytes': output.stat().st_size,
                          'onnx_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
        print(json.dumps({'asset': name, 'status': 'downloaded_and_extracted'}), flush=True)
    (root / 'assets.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
