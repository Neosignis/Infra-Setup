"""Bounded CPU adapter fit on real prepared ASL poses; no production promotion."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import resource
import time

from neosignis.training.adapter import (build_adapter, encode_source, evaluate_loss, fit_step, freeze_base,
                                       generate_text, prepare_labels, select_training)
from neosignis.training.how2sign import sha256_file
from neosignis.training.pose import torch_unisign_collate
from neosignis.training.prepared import PreparedPoseDataset
from neosignis.training.unisign_runtime import CHECKPOINT_SHA, load_unisign


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1'))
    parser.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--examples', type=int, default=8)
    parser.add_argument('--steps', type=int, default=32)
    parser.add_argument('--rank', type=int, default=16)
    parser.add_argument('--seed', type=int, default=20261118)
    parser.add_argument('--learning-rate', type=float, default=0.0003)
    parser.add_argument('--max-seconds', type=int, default=720)
    args = parser.parse_args()
    if (not 1 <= args.examples <= 32 or not 1 <= args.steps <= 64 or not 1 <= args.rank <= 32
            or not math.isfinite(args.learning_rate) or not 0 < args.learning_rate <= .01
            or not 60 <= args.max_seconds <= 1200):
        parser.error('Experiment exceeds bounded local configuration')
    if args.output.resolve().is_relative_to(args.data_root.resolve()) or args.output.resolve().is_relative_to(args.model_root.resolve()):
        parser.error('Experiment output must be separate from source data and model assets')
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    os.environ.setdefault('HF_HOME', str((args.model_root / 'hf-cache').resolve()))
    import torch
    torch.set_num_threads(2); torch.manual_seed(args.seed); torch.use_deterministic_algorithms(True)
    train = PreparedPoseDataset(args.data_root / 'train', split='train', usage='training')
    val = PreparedPoseDataset(args.data_root / 'val', split='val', usage='evaluation')
    if {r['source_video_group'] for r in train.records} & {r['source_video_group'] for r in val.records}:
        raise ValueError('Training and validation source videos overlap')
    print(json.dumps({'stage': 'loading_frozen_baseline', 'device': 'cpu'}), flush=True)
    model = load_unisign(args.model_root, device='cpu'); freeze_base(model)
    adapter = build_adapter(model.mt5_model.config.d_model, args.rank)
    selected, excluded = select_training(train, model.mt5_tokenizer, count=args.examples)
    config = {'schema_version': 'neosignis.asl-adapter-experiment.v1', 'started_at': datetime.now(timezone.utc).isoformat(),
              'device': 'cpu', 'torch_version': torch.__version__, 'seed': args.seed, 'steps_requested': args.steps,
              'learning_rate': args.learning_rate, 'rank': args.rank, 'hidden_size': model.mt5_model.config.d_model,
              'trainable_parameters': sum(p.numel() for p in adapter.parameters()),
              'frozen_base_parameters': sum(p.numel() for p in model.parameters()),
              'base_checkpoint_sha256': CHECKPOINT_SHA,
              'train_manifest_sha256': sha256_file(args.data_root / 'train/manifest.json'),
              'val_manifest_sha256': sha256_file(args.data_root / 'val/manifest.json'),
              'training_ids': [train[i].id for i in selected], 'validation_ids': [val[i].id for i in range(len(val))],
              'excluded_training_examples': excluded, 'signer_disjointness_verified': False,
              'alignment_review_complete': False, 'production_promotion': False}
    write_json(args.output / 'config.json', config)
    cached = {'train': [], 'val': []}
    for split, dataset, indices in [('train', train, selected), ('val', val, range(len(val)))]:
        for index in indices:
            if time.monotonic() - started > args.max_seconds:
                raise TimeoutError('Preparation exceeded local experiment time bound')
            sample = dataset[index]
            source, _ = torch_unisign_collate([sample])
            encoded, mask = encode_source(model, source)
            labels = prepare_labels(model.mt5_tokenizer, [sample.text])
            cached[split].append({'id': sample.id, 'text': sample.text, 'encoded': encoded, 'mask': mask, 'labels': labels})
            print(json.dumps({'stage': 'encoded', 'split': split, 'examples': len(cached[split]),
                              'frames': len(sample.features)}), flush=True)
    print(json.dumps({'stage': 'measuring_before_training'}), flush=True)
    before = {split: evaluate_loss(model.mt5_model, adapter, samples) for split, samples in cached.items()}
    for sample in cached['val']:
        sample['prediction_before'] = generate_text(model.mt5_model, model.mt5_tokenizer, adapter, sample)
    write_json(args.output / 'before.json', before)
    initial = {key: value.detach().clone() for key, value in adapter.state_dict().items()}
    optimizer = torch.optim.AdamW(adapter.parameters(), lr=args.learning_rate, weight_decay=.01)
    order, completed = [], 0
    with (args.output / 'steps.jsonl').open('w') as log:
        for step in range(args.steps):
            if time.monotonic() - started > args.max_seconds:
                break
            if not order: order = torch.randperm(len(cached['train'])).tolist()
            sample = cached['train'][order.pop()]
            tick = time.monotonic()
            loss, norm = fit_step(model.mt5_model, adapter, optimizer, sample['encoded'], sample['mask'], sample['labels'])
            completed += 1
            record = {'step': completed, 'split': 'train', 'id': sample['id'], 'loss': loss,
                      'gradient_norm_before_clip': norm, 'elapsed_s': round(time.monotonic() - tick, 3)}
            log.write(json.dumps(record) + '\n'); log.flush()
            print(json.dumps({key: value for key, value in record.items() if key != 'id'}), flush=True)
    changed = [key for key, value in adapter.state_dict().items() if not torch.equal(value, initial[key])]
    if not completed or not changed:
        raise ValueError('No successful adapter update occurred')
    print(json.dumps({'stage': 'measuring_after_training'}), flush=True)
    after = {split: evaluate_loss(model.mt5_model, adapter, samples) for split, samples in cached.items()}
    predictions = [{'id': sample['id'], 'reference': sample['text'], 'before': sample['prediction_before'],
                    'after': generate_text(model.mt5_model, model.mt5_tokenizer, adapter, sample)} for sample in cached['val']]
    checkpoint_path = args.output / 'adapter.pt'
    torch.save({'schema_version': 'neosignis.asl-encoder-adapter.v1', 'rank': args.rank,
                'hidden_size': config['hidden_size'], 'base_checkpoint_sha256': CHECKPOINT_SHA,
                'adapter_state_dict': adapter.state_dict(), 'steps': completed, 'seed': args.seed,
                'train_manifest_sha256': config['train_manifest_sha256'],
                'val_manifest_sha256': config['val_manifest_sha256']}, checkpoint_path)
    restored = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    fresh = build_adapter(config['hidden_size'], args.rank)
    fresh.load_state_dict(restored['adapter_state_dict'], strict=True)
    if any(not torch.equal(value, fresh.state_dict()[key]) for key, value in adapter.state_dict().items()):
        raise ValueError('Saved adapter differs after restoration')
    source_unchanged = sha256_file(args.model_root / 'how2sign_pose_only_slt.pth') == CHECKPOINT_SHA
    report = {'status': 'small_adapter_training_completed', 'training_run': True, 'optimizer_steps': completed,
              'all_requested_steps_completed': completed == args.steps, 'training_examples': len(cached['train']),
              'validation_examples': len(cached['val']), 'trainable_parameters': config['trainable_parameters'],
              'frozen_base_parameters': config['frozen_base_parameters'], 'before': before, 'after': after,
              'changed_adapter_tensors': changed, 'frozen_base_gradients_none': all(p.grad is None for p in model.parameters()),
              'source_checkpoint_unchanged': source_unchanged, 'checkpoint_roundtrip_passed': True,
              'adapter_checkpoint_sha256': sha256_file(checkpoint_path), 'adapter_checkpoint_bytes': checkpoint_path.stat().st_size,
              'elapsed_s': round(time.monotonic() - started, 2), 'peak_process_rss_bytes_macos': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'semantic_accuracy_measured': False, 'real_time_validated': False, 'signer_disjointness_verified': False,
              'production_promotion': False, 'note': 'Small training-process experiment on an already How2Sign-pretrained model; loss is not ASL comprehension.'}
    if not source_unchanged: raise ValueError('Original model checkpoint changed')
    write_json(args.output / 'validation-predictions.private.json', predictions)
    write_json(args.output / 'report.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__': main()
