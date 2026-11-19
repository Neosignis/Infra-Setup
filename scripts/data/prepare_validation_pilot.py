"""Index existing validation footage and cache two complete timestamped poses."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

from neosignis.training.how2sign import How2SignArchive
from neosignis.training.pose import POSE_SCHEMA, load_local_pose_extractor, unisign_collate
from neosignis.training.prepared import PreparedPoseDataset, save_numeric


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, default=Path('/Users/user/Downloads/val_rgb_front_clips.zip'))
    p.add_argument('--inventory', type=Path, default=Path('data/local/how2sign/research-only/val/front/val_rgb_front_clips.integrity.json'))
    p.add_argument('--references', type=Path, default=Path('data/local/how2sign/research-only/val/annotations/how2sign_val.csv'))
    p.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    p.add_argument('--output', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1/val'))
    p.add_argument('--count', type=int, default=2)
    args = p.parse_args()
    if not 1 <= args.count <= 8: p.error('Small CPU feature pilot supports 1..8 clips')
    if (args.output / 'manifest.json').exists(): p.error('Validation pilot already exists; choose a new output')
    source = How2SignArchive(args.archive, args.inventory, args.references, split='val', usage='evaluation')
    rows = {r['SENTENCE_NAME']: r for r in csv.DictReader(args.references.open(), delimiter='\t')}
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.output / 'catalogue.jsonl').open('w') as stream:
        for clip in source.records:
            stream.write(json.dumps({'id': clip.id, 'publisher_split': 'val', 'member': clip.member,
                                     'video_sha256': clip.sha256, 'text': clip.text,
                                     'source_video_group': rows[clip.id]['VIDEO_ID'], 'signer_id': None,
                                     'alignment_review': 'pending', 'training_eligible': False}) + '\n')
    quarantine = {'missing_video_ids': source.missing_video_ids, 'unreferenced_video_ids': source.unreferenced_video_ids,
                  'publisher_split': 'val', 'training_eligible': False}
    (args.output / 'quarantine.json').write_text(json.dumps(quarantine, indent=2) + '\n')
    # A small CPU mechanics sample. Selection is by reference duration only;
    # it does not assert that the annotations align with the actual video.
    ordered = sorted(range(len(source)), key=lambda i: (
        source.records[i].reference_end_s - source.records[i].reference_start_s,
        hashlib.sha256(source.records[i].id.encode()).hexdigest()))
    selected, groups = [], set()
    for index in ordered:
        clip = source.records[index]
        group = rows[clip.id]['VIDEO_ID']
        if clip.reference_end_s - clip.reference_start_s < 1 or group in groups: continue
        selected.append(index); groups.add(group)
        if len(selected) == args.count: break
    extractor = load_local_pose_extractor(args.model_root)
    records = []
    for index in selected:
        started = time.monotonic()
        sample = source.load(index, extractor, feature_schema=POSE_SCHEMA, extractor_version=extractor.version)
        unisign_collate([sample])
        numeric = save_numeric(sample, args.output / (sample.id + '.npz'))
        clip = source.records[index]
        records.append({'id': sample.id, 'text': sample.text, 'publisher_split': 'val',
                        'source_member': clip.member, 'video_sha256': clip.sha256,
                        'source_video_group': rows[sample.id]['VIDEO_ID'], 'signer_id': None,
                        'reference_start_s': clip.reference_start_s, 'reference_end_s': clip.reference_end_s,
                        'alignment_review': 'pending', 'linguistic_review': 'pending',
                        'feature_schema': POSE_SCHEMA, 'extractor_version': extractor.version,
                        'numeric': numeric})
        print(json.dumps({'validation_prepared': len(records), 'frames': len(sample.features),
                          'last_pts_ms': float(sample.timestamps_ms[-1]), 'elapsed_s': round(time.monotonic() - started, 2)}), flush=True)
    manifest = {'schema_version': 'neosignis.prepared-pose-pilot.v1', 'publisher_split': 'val',
                'purpose': 'development_validation_not_training_or_final_holdout',
                'feature_schema': POSE_SCHEMA, 'extractor_version': extractor.version,
                'source_archive_sha256': source.archive_sha256, 'references_sha256': source.references_sha256,
                'catalogued_clips': len(source), 'missing_video_rows': len(source.missing_video_ids),
                'records': records, 'signer_disjointness_verified': False, 'alignment_review_complete': False,
                'training_run': False, 'training_eligible': False}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    dataset = PreparedPoseDataset(args.output, split='val', usage='evaluation')
    for index in range(len(dataset)): unisign_collate([dataset[index]])
    print(json.dumps({'catalogued': len(source), 'numeric_validation_utterances': len(dataset),
                      'missing_video_rows_quarantined': len(source.missing_video_ids), 'training_run': False}), flush=True)


if __name__ == '__main__': main()
