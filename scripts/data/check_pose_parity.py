"""Compare numeric pose conversion with two pinned upstream pure functions.

Uses synthetic arrays, not ASL training data. Does not import upstream dataset
classes, run arbitrary module-level code or download anything.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from neosignis.training.pose import POSE_SCHEMA, unisign_parts
from neosignis.training.utterances import Utterance


def main():
    root = Path('data/local/models/unisign')
    path = root / 'source/datasets.py'
    receipt = json.loads((root / 'acquisition.json').read_text())
    record = next(r for r in receipt['assets'] if Path(r['file']).resolve() == path.resolve())
    if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Upstream source changed')
    parsed = ast.parse(path.read_text())
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)
                 and node.name in {'load_part_kp', 'crop_scale'}]
    if len(functions) != 2:
        raise ValueError('Expected exactly the two reviewed conversion functions')
    namespace = {'np': np, 'torch': torch, 'copy': copy}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    generator = np.random.default_rng(7)
    cases, maximum = 0, 0.0
    for count in [1, 4, 21, 351]:
        values = generator.uniform(0, 1, (count, 133, 3)).astype(np.float32)
        values[:, :, 2] = .9
        values[:, 20:30, 2] = .1
        values[:, 40:50, 2] = 1.5
        values[:, 60:70, 2] = -.1
        if count > 1:
            values[1] = 0
        observed = np.repeat((values[:, :, 2] > .3)[:, :, None], 3, axis=2)
        sample = Utterance('synthetic', 'Synthetic target.', 'val', values.reshape(count, 399),
                           observed.reshape(count, 399), np.arange(count, dtype=np.float64) * 40,
                           POSE_SCHEMA, 'parity-fixture.v1')
        actual, _ = unisign_parts(sample)
        reference = namespace['load_part_kp']([v[None, :, :2] for v in values],
                                             [v[None, :, 2] for v in values])
        for part in actual:
            expected = reference[part].numpy()
            np.testing.assert_allclose(actual[part], expected, atol=1e-6, rtol=1e-6)
            maximum = max(maximum, float(np.max(np.abs(actual[part] - expected))))
        cases += 1
    result = {'checked_at': '2026-11-18', 'source_revision': receipt['code_revision'],
              'synthetic_cases_passed': cases, 'maximum_absolute_difference': maximum,
              'real_extractor_parity_checked': False, 'asl_accuracy_measured': False}
    Path('docs/data/pose-numerical-parity-2026-11-18.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
