"""Read local compute readiness and exercise a tiny synthetic optimizer step.

This never downloads/loads Uni-Sign or trains on ASL data.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--device', choices=['auto', 'cpu', 'mps'], default='auto')
    args = parser.parse_args()
    import torch
    memory = None
    if platform.system() == 'Darwin':
        result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            memory = int(result.stdout.strip())
    available = torch.backends.mps.is_available()
    device = 'mps' if args.device == 'auto' and available else ('cpu' if args.device == 'auto' else args.device)
    if device == 'mps' and not available:
        parser.error('MPS is unavailable in this process; no silent device fallback')
    torch.manual_seed(7)
    model = torch.nn.Linear(4, 2).to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=.01)
    values = torch.ones((2, 4), dtype=torch.float32, device=device)
    before = model.weight.detach().cpu().clone()
    optimizer.zero_grad()
    loss = model(values).square().mean()
    loss.backward()
    optimizer.step()
    if device == 'mps':
        torch.mps.synchronize()
    result = {'schema_version': 'neosignis.local-compute-check.v1', 'machine': platform.machine(),
              'torch_version': torch.__version__, 'physical_memory_bytes': memory,
              'disk_free_bytes': shutil.disk_usage('.').free,
              'mps_built': torch.backends.mps.is_built(), 'mps_available_in_process': available,
              'tested_device': device, 'synthetic_optimizer_step_passed': not torch.equal(before, model.weight.detach().cpu()),
              'missing_optional_runtime_packages': [name for name in ('rtmlib', 'onnxruntime', 'transformers', 'sentencepiece')
                                                    if importlib.util.find_spec(name) is None],
              'unisign_loaded': False, 'asl_training_run': False, 'model_accuracy_measured': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
