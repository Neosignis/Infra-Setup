"""Prepare a bounded genuine How2Sign training pose pilot; never fit a model.

Pinned publisher annotations + ZIP ranges. Whole source parts are not downloaded.
All source splits remain intact; local validation source groups are excluded.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
from zipfile import ZipFile

from neosignis.training.how2sign import sha256_file
from neosignis.training.pose import POSE_SCHEMA, unisign_collate
from neosignis.training.prepared import (PUBLISHER_EXTRACTOR, PreparedPoseDataset, convert_publisher_pose,
                                        load_publisher_labels, save_numeric, select_pilot, source_group)
from neosignis.training.remote_zip import MultipartRangeReader

REPO = 'ZechengLi19/Uni-Sign'
POSE_REVISION = 'eab251b7fe7e8521afc0e67be98add670ea40a0d'
CODE_REVISION = 'eed438bcb49e30405cd6ccdfcccca330c134e830'
LABELS_SHA256 = '3780dc31ec64f6cb1daff76f6bece88b9f5bf365024e9fd97a49d0244a910828'


def acquire_sources(metadata, labels):
    """Only small source metadata/annotations; no full video or pose archive."""
    metadata, labels = Path(metadata), Path(labels)
    for path in (metadata, labels):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise ValueError('Refusing symlink source destination')
    if not metadata.exists():
        url = f'https://huggingface.co/api/models/{REPO}/revision/{POSE_REVISION}?blobs=true'
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read(2 * 1024**2 + 1)
        if len(body) > 2 * 1024**2:
            raise ValueError('Publisher metadata exceeds size bound')
        data = json.loads(body)
        if data['sha'] != POSE_REVISION:
            raise ValueError('Publisher metadata revision changed')
        parts = [part for part in data['siblings'] if part['rfilename'].startswith('how2sign_pose_format.zip.')]
        write_json(metadata, {'repo': REPO, 'revision': POSE_REVISION, 'parts': sorted(parts, key=lambda part: part['rfilename'])})
    if not labels.exists():
        url = f'https://raw.githubusercontent.com/{REPO}/{CODE_REVISION}/data/How2Sign/labels.train'
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read(4 * 1024**2 + 1)
        if len(body) > 4 * 1024**2 or hashlib.sha256(body).hexdigest() != LABELS_SHA256:
            raise ValueError('Pinned publisher training annotations differ')
        labels.write_bytes(body)


def write_json(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def prepare(metadata, labels_path, val_references, output, *, count=32, transfer_mib=64):
    if not 16 <= transfer_mib <= 256:
        raise ValueError('Transfer budget must be 16..256 MiB')
    metadata, labels_path, val_references, output = map(Path, (metadata, labels_path, val_references, output))
    info = json.loads(metadata.read_text())
    if info['repo'] != REPO or info['revision'] != POSE_REVISION or len(info['parts']) != 4:
        raise ValueError('Unrecognized publisher snapshot')
    labels = load_publisher_labels(labels_path)
    with val_references.open(newline='', encoding='utf-8-sig') as stream:
        validation = list(csv.DictReader(stream, delimiter='\t'))
    val_groups = {row['VIDEO_ID'] for row in validation}
    train_groups = {source_group(key) for key in labels}
    overlap = train_groups & val_groups
    if overlap:
        raise ValueError('Training annotations overlap local validation source videos')
    parts = []
    for n, part in enumerate(info['parts']):
        if part['rfilename'] != f'how2sign_pose_format.zip.{n:02d}':
            raise ValueError('Publisher multipart order changed')
        parts.append({'size': part['size'], 'url': f'https://huggingface.co/{REPO}/resolve/{POSE_REVISION}/{part["rfilename"]}'})
    labels_hash, val_hash = sha256_file(labels_path), sha256_file(val_references)
    if labels_hash != LABELS_SHA256:
        raise ValueError('Training annotation hash differs from pinned source')
    identity = {'pose_revision': POSE_REVISION, 'labels_revision': CODE_REVISION,
                'labels_sha256': labels_hash, 'validation_references_sha256': val_hash,
                'selection': 'neosignis-pilot-v1:sha256-one-utterance-per-source-video', 'requested_count': count}
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.is_symlink() or shutil.disk_usage(output).free < 2 * 1024**3:
        raise ValueError('Local pilot requires a real directory and 2 GiB free headroom')
    identity_path = output / 'identity.json'
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise ValueError('Existing output belongs to a different dataset selection')
    write_json(identity_path, identity)
    records = []
    with MultipartRangeReader(parts, budget_bytes=transfer_mib * 1024**2, block_bytes=512 * 1024) as reader:
        with ZipFile(reader) as archive:
            files = archive.infolist()
            if len(files) > 100000:
                raise ValueError('Publisher directory exceeds member bound')
            entries = [{'path': f.filename, 'bytes': f.file_size, 'compressed_bytes': f.compress_size} for f in files]
            selected = select_pilot(labels, entries, count=count, excluded_groups=val_groups)
            for index, (key, member) in enumerate(selected, start=1):
                id_ = key[:-4]
                receipt_path = output / (id_ + '.json')
                if receipt_path.exists():
                    record = json.loads(receipt_path.read_text())
                    if (record['id'] != id_ or record['text'] != labels[key]['text']
                            or record['source_member'] != member['path']
                            or record['publisher_split'] != 'train'):
                        raise ValueError('Resume receipt differs from selection')
                    numeric_path = output / record['numeric']['path']
                    if numeric_path.parent != output or sha256_file(numeric_path) != record['numeric']['sha256']:
                        raise ValueError('Resume numeric cache changed')
                else:
                    item = archive.getinfo(member['path'])
                    if item.flag_bits & 1 or item.compress_size > 32 * 1024**2 or not 0 < item.file_size <= 32 * 1024**2:
                        raise ValueError('Unsupported publisher pose member')
                    payload = archive.read(item)  # ZIP CRC is checked here.
                    sample = convert_publisher_pose(payload, name=id_, text=labels[key]['text'], split='train')
                    numeric = save_numeric(sample, output / (id_ + '.npz'))
                    record = {'id': id_, 'publisher_split': 'train', 'text': sample.text,
                              'source_video_group': source_group(key), 'signer_id': None,
                              'source_member': member['path'], 'source_pose_sha256': hashlib.sha256(payload).hexdigest(),
                              'source_pose_crc32': item.CRC, 'source_pose_bytes': len(payload),
                              'feature_schema': POSE_SCHEMA, 'extractor_version': PUBLISHER_EXTRACTOR,
                              'alignment_review': 'pending', 'linguistic_review': 'pending', 'numeric': numeric}
                    write_json(receipt_path, record)
                records.append(record)
                print(json.dumps({'prepared': index, 'total': count, 'frames': record['numeric']['frames'],
                                  'transfer_bytes': reader.transferred}), flush=True)
        transfer = {'bytes': reader.transferred, 'requests': reader.requests, 'limit_bytes': reader.budget,
                    'whole_parts_downloaded': False, 'whole_part_sha256_verified': False}
    manifest = {'schema_version': 'neosignis.prepared-pose-pilot.v1', 'created_at': datetime.now(timezone.utc).isoformat(),
                'purpose': 'experimental_training_process_pilot_not_mvp_quality', 'publisher_split': 'train',
                'feature_schema': POSE_SCHEMA, 'extractor_version': PUBLISHER_EXTRACTOR,
                'owner_authorization_record': 'project-owner-proceed-with-selected-model-experiments-2026-11-18',
                'publisher_annotation_source': f'https://github.com/{REPO}/blob/{CODE_REVISION}/data/How2Sign/labels.train',
                'source_identity': identity, 'pose_parts': info['parts'], 'transfer': transfer,
                'records': records, 'publisher_train_annotations': len(labels),
                'source_video_overlap_with_local_val': 0, 'validation_source_videos': len(val_groups),
                'signer_disjointness_verified': False, 'alignment_review_complete': False,
                'linguistic_review_complete': False, 'timestamps': 'unavailable_source_frame_order_only',
                'source_timing_reconstructed': False, 'raw_training_videos_downloaded': False,
                'training_run': False, 'product_quality_approved': False}
    write_json(output / 'manifest.json', manifest)
    dataset = PreparedPoseDataset(output, split='train', usage='inspection')
    for index in range(len(dataset)):
        unisign_collate([dataset[index]])
    result = {'status': 'numeric_training_pilot_prepared', 'utterances': len(dataset),
              'source_video_groups': len({r['source_video_group'] for r in records}),
              'frames': sum(r['numeric']['frames'] for r in records),
              'numeric_bytes': sum(r['numeric']['bytes'] for r in records),
              'training_run': False, 'alignment_review_complete': False, 'signer_disjointness_verified': False,
              'transfer': transfer, 'manifest_sha256': sha256_file(output / 'manifest.json')}
    write_json(output / 'summary.json', result)
    print(json.dumps(result, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, default=Path('data/local/how2sign/preparation/pose-parts.json'))
    parser.add_argument('--labels', type=Path, default=Path('data/local/how2sign/preparation/labels.train.source'))
    parser.add_argument('--validation-references', type=Path, default=Path('data/local/how2sign/research-only/val/annotations/how2sign_val.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1/train'))
    parser.add_argument('--count', type=int, default=32)
    parser.add_argument('--transfer-mib', type=int, default=64)
    args = parser.parse_args()
    if not args.validation_references.is_file():
        parser.error('Provide the checked local validation references; they are needed for split leakage checks')
    acquire_sources(args.metadata, args.labels)
    prepare(args.metadata, args.labels, args.validation_references, args.output,
            count=args.count, transfer_mib=args.transfer_mib)


if __name__ == '__main__':
    main()
