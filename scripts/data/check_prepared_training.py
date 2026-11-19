"""Check prepared numeric inputs, full targets and source-group separation; no fit."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from neosignis.training.pose import torch_unisign_collate
from neosignis.training.prepared import PreparedPoseDataset
from neosignis.training.unisign_runtime import verified_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1'))
    parser.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    args = parser.parse_args()
    os.environ.setdefault('HF_HOME', str((args.model_root / 'hf-cache').resolve()))
    from torch.utils.data import DataLoader
    from transformers import T5Tokenizer
    model_root = verified_bundle(args.model_root)
    tokenizer = T5Tokenizer.from_pretrained(model_root / 'decoder', local_files_only=True)
    train = PreparedPoseDataset(args.root / 'train', split='train', usage='inspection')
    val = PreparedPoseDataset(args.root / 'val', split='val', usage='evaluation')
    train_groups = {r['source_video_group'] for r in train.records}
    val_groups = {r['source_video_group'] for r in val.records}
    if (train_groups & val_groups
            or {r['id'] for r in train.records} & {r['id'] for r in val.records}
            or {r['numeric']['sha256'] for r in train.records} & {r['numeric']['sha256'] for r in val.records}
            or train.manifest['source_identity']['validation_references_sha256'] != val.manifest['references_sha256']):
        raise ValueError('Train/validation data identities overlap or differ from split-audit sources')
    lengths, tokens, qc, flagged = [], [], [], []
    for index in range(len(train)):
        sample = train[index]
        lengths.append(len(sample.features)); tokens.append(len(tokenizer.encode(sample.text, truncation=False)))
        scores = sample.features.reshape(-1, 133, 3)[:, :, 2]
        body = float(((scores[:, [0, 3, 4, 5, 6, 7, 8, 9, 10]] > .3).sum(axis=1) >= 4).mean())
        hands = float(((scores[:, 91:] > .3).sum(axis=1) >= 8).mean())
        reasons = []
        if len(sample.features) < 16: reasons.append('fewer_than_16_frames_review_complete_utterance')
        if body < .6: reasons.append('low_body_visibility')
        if hands < .6: reasons.append('low_hand_visibility')
        qc.append({'id': sample.id, 'visible_body_frame_fraction': round(body, 4),
                   'visible_hands_frame_fraction': round(hands, 4), 'review_flags': reasons})
        if reasons: flagged.append(sample.id)
    for split, dataset in [('train', train), ('val', val)]:
        for index in range(len(dataset)):
            sample = dataset[index]
            source, target = torch_unisign_collate([sample])
            if int(source['attention_mask'].sum()) != len(sample.features) or target['gt_sentence'][0] != sample.text:
                raise ValueError('Collation truncated a source sequence or target')
        with (args.root / split / 'index.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['id', 'publisher_split', 'source_video_group', 'signer_id', 'frames', 'timing', 'text', 'alignment_review', 'numeric_file'])
            for r in dataset.records:
                writer.writerow([r['id'], split, r['source_video_group'], 'unknown', r['numeric']['frames'],
                                 r['numeric']['timestamps'], r['text'], 'pending', r['numeric']['path']])
    loader = DataLoader(train, batch_size=2, num_workers=0, collate_fn=torch_unisign_collate)
    source, _ = next(iter(loader))
    if source['body'].shape[0] != 2:
        raise ValueError('Unexpected DataLoader batch')
    report = {'status': 'prepared_pilot_loader_check_passed', 'training_utterances': len(train),
              'validation_feature_utterances': len(val), 'train_frames': sum(lengths),
              'training_frame_range': [min(lengths), max(lengths)], 'target_token_range': [min(tokens), max(tokens)],
              'tokenizer': 'same local T5Tokenizer as Uni-Sign runtime; truncation disabled',
              'data_loader_batch_size_checked': 2, 'validation_catalogued': val.manifest['catalogued_clips'],
              'validation_missing_videos': val.manifest['missing_video_rows'], 'train_val_source_video_overlap': 0,
              'signer_disjointness_verified': False, 'training_timestamps_known': False, 'validation_pts_preserved': True,
              'quality_metrics_are_pose_visibility_only': True, 'alignment_review_complete': False,
              'training_run': False, 'optimizer_steps': 0, 'all_numeric_files_hash_checked': True,
              'all_pilot_frames_and_targets_retained': True, 'pose_visibility': qc,
              'utterances_flagged_for_extra_review': flagged,
              'training_manifest_sha256': hashlib.sha256((args.root / 'train/manifest.json').read_bytes()).hexdigest(),
              'validation_manifest_sha256': hashlib.sha256((args.root / 'val/manifest.json').read_bytes()).hexdigest()}
    (args.root / 'readiness.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'pose_visibility'}, indent=2))


if __name__ == '__main__': main()
