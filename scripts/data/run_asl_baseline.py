"""One complete local validation clip -> ASL pose -> English prediction.

Output stays private. This command does not train or score linguistic accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from neosignis.training.how2sign import How2SignArchive
from neosignis.training.pose import POSE_SCHEMA, DetectedSignerPredictor, WholeBodyFrameExtractor, torch_unisign_collate
from neosignis.training.unisign_runtime import load_unisign, translate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=['cpu', 'mps'], default='cpu')
    parser.add_argument('--max-new-tokens', type=int, default=40)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.archive, args.inventory, args.references)}:
        raise ValueError('Output must not overwrite a source input')
    if not 1 <= args.max_new_tokens <= 512:
        raise ValueError('Output token budget must be 1..512')
    import torch
    from rtmlib import Wholebody
    torch.set_num_threads(2)
    source = How2SignArchive(args.archive, args.inventory, args.references, split='val')
    candidates = [i for i, c in enumerate(source.records) if 2 <= c.reference_end_s - c.reference_start_s <= 5]
    if not candidates:
        raise ValueError('No bounded full-utterance baseline candidate')
    index = sorted(candidates, key=lambda i: source.records[i].id)[0]
    manifest = json.loads((args.model_root / 'pose/assets.json').read_text())
    for record in manifest.values():
        if hashlib.sha256(Path(record['onnx']).read_bytes()).hexdigest() != record['onnx_sha256']:
            raise ValueError('Pose asset hash mismatch')
    predictor = Wholebody(det=manifest['detector']['onnx'], det_input_size=(416, 416),
                          pose=manifest['pose']['onnx'], pose_input_size=(192, 256),
                          to_openpose=False, backend='onnxruntime', device='cpu')
    predictor = DetectedSignerPredictor(predictor.det_model, predictor.pose_model)
    extractor = WholeBodyFrameExtractor(predictor, version='rtmlib.0.0.13.local-lightweight.raw-simcc-v1')
    print(json.dumps({'stage': 'extracting_poses', 'reference_duration_s': source.records[index].reference_end_s - source.records[index].reference_start_s}), flush=True)
    started = time.monotonic()
    sample = source.load(index, extractor, feature_schema=POSE_SCHEMA, extractor_version=extractor.version)
    extracted = time.monotonic()
    print(json.dumps({'stage': 'poses_extracted', 'frames': len(sample.features)}), flush=True)
    batch, _targets = torch_unisign_collate([sample])
    batch = {k: v.to(args.device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
    model = load_unisign(args.model_root, device=args.device)
    loaded = time.monotonic()
    print(json.dumps({'stage': 'translating', 'device': args.device}), flush=True)
    predictions = translate(model, batch, max_new_tokens=args.max_new_tokens)
    if args.device == 'mps':
        torch.mps.synchronize()
    finished = time.monotonic()
    result = {'status': 'prediction_produced', 'source_split': 'val', 'clip_id': sample.id,
              'reference_text': sample.text, 'predicted_text': predictions[0],
              'frames': len(sample.features), 'last_pts_ms': float(sample.timestamps_ms[-1]),
              'device': args.device, 'pose_elapsed_s': round(extracted - started, 3),
              'model_load_s': round(loaded - extracted, 3), 'translation_elapsed_s': round(finished - loaded, 3),
              'training_run': False, 'linguistic_accuracy_approved': False,
              'note': 'One development prediction is not a benchmark or real-time acceptance result.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in {'clip_id', 'reference_text', 'predicted_text'}}, indent=2))


if __name__ == '__main__':
    main()
