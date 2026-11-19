"""Reload the saved adapter and evaluate the declared development samples only."""
import argparse
import json
import os
from pathlib import Path

from neosignis.training.adapter import encode_source, evaluate_loss, freeze_base, generate_text, load_trained_adapter, prepare_labels
from neosignis.training.how2sign import sha256_file
from neosignis.training.pose import torch_unisign_collate
from neosignis.training.prepared import PreparedPoseDataset
from neosignis.training.unisign_runtime import CHECKPOINT_SHA, load_unisign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1'))
    parser.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.data_root.resolve()) or args.output.resolve().is_relative_to(args.model_root.resolve()):
        parser.error('Use a new evaluation output outside source data/model folders')
    report = json.loads((args.run_dir / 'report.json').read_text())
    adapter, checkpoint = load_trained_adapter(args.run_dir / 'adapter.pt', expected_sha256=report['adapter_checkpoint_sha256'],
                                               expected_base_sha256=CHECKPOINT_SHA)
    if sha256_file(args.data_root / 'val/manifest.json') != checkpoint['val_manifest_sha256']:
        raise ValueError('Evaluation manifest differs from declared experiment')
    os.environ.setdefault('HF_HOME', str((args.model_root / 'hf-cache').resolve()))
    import torch
    torch.set_num_threads(2)
    base = load_unisign(args.model_root); freeze_base(base)
    dataset = PreparedPoseDataset(args.data_root / 'val', split='val', usage='evaluation')
    samples = []
    for index in range(len(dataset)):
        utterance = dataset[index]
        source, _ = torch_unisign_collate([utterance])
        encoded, mask = encode_source(base, source)
        samples.append({'id': utterance.id, 'text': utterance.text, 'encoded': encoded, 'mask': mask,
                        'labels': prepare_labels(base.mt5_tokenizer, [utterance.text])})
    loss = evaluate_loss(base.mt5_model, adapter, samples)
    predictions = [{'id': sample['id'], 'reference': sample['text'],
                    'prediction': generate_text(base.mt5_model, base.mt5_tokenizer, adapter, sample)} for sample in samples]
    result = {'status': 'saved_adapter_evaluation_completed', 'optimizer_steps': 0, 'validation_examples': len(samples),
              'loss': loss, 'predictions': predictions, 'semantic_accuracy_measured': False, 'production_promotion': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in {'predictions', 'loss'}} |
                     {'token_weighted_cross_entropy': loss['token_weighted_cross_entropy']}, indent=2))


if __name__ == '__main__': main()
