# First local ASL adapter training

18 November 2026. **A small training run completed on this Mac. It did not improve validation translation.**

| Item | Result |
|---|---:|
| Training examples | 8 genuine publisher-training utterances |
| Development validation examples | 2, excluded from fitting |
| Trainable adapter parameters | 25,360 |
| Frozen pretrained baseline parameters | 587,747,368 |
| Optimizer updates | 32 |
| End-to-end experiment time | 45.79 seconds on CPU |
| Saved adapter | 104,157 bytes |

The adapter is a small residual network between the frozen encoder and decoder. Frozen encoder features are cached in memory during the experiment. Only the adapter receives optimizer updates. **The original large model is still required; this is not a standalone 104 KB translator.** This work targets ASL-to-English, not English-to-ASL signing output.

## What the measurements show

| Token-weighted cross-entropy loss; lower is better | Before | After |
|---|---:|---:|
| Eight training examples | 0.7493 | 0.6349 |
| Two development validation examples | 3.8070 | 3.8395 |

Training loss decreased, showing that the adapter can fit its training examples. Validation loss rose slightly. Both generated validation predictions stayed unchanged and differed from their supplied English references. Loss measures likelihood of the reference under teacher forcing; it is not a percentage accuracy or a Deaf-user comprehension score. There is no demonstrated generalization improvement.

The baseline was already pretrained on How2Sign. This tiny experiment does not establish learning new signs, performance on independent signers, real-time speed or everyday-MVP coverage. Source-video groups are separate, but signer identity and video/text alignment still need verification. The nine-frame example flagged during preparation was excluded before fitting, along with examples outside the fixed frame/token budgets. All exclusions and the deterministic eight-example selection are recorded.

## Files and reproduction

Private local files, ignored by Git:

```text
data/local/runs/asl-adapter-pilot-2026-11-18/
  adapter.pt                          hash-pinned adapter tensor checkpoint
  config.json                         seed, data hashes, IDs and exclusions
  steps.jsonl                         loss and gradient norm per training update
  report.json                         before/after losses and integrity checks
  validation-predictions.private.json  references and generated predictions
  reloaded-evaluation.private.json     separate saved-checkpoint evaluation
```

To inspect the saved model again without fitting:

```sh
PYTHONPATH=src .venv-ml/bin/python scripts/data/evaluate_asl_adapter.py \
  --run-dir data/local/runs/asl-adapter-pilot-2026-11-18 \
  --output data/local/runs/asl-adapter-pilot-2026-11-18/another-evaluation.private.json
```

Use a new output filename. A fresh bounded run uses:

```sh
PYTHONPATH=src .venv-ml/bin/python scripts/data/train_asl_adapter.py \
  --output data/local/runs/asl-adapter-pilot-next \
  --examples 8 --steps 32 --rank 16 --learning-rate 0.0003
```

Seed `20261118`, CPU, two threads, batch size one, gradient clipping and no target truncation. The script bounds preparation/fitting time and saves a separate adapter; final evaluation/checkpoint writing follow. Prepared training examples must be publisher `train`. No validation references enter generation or optimizer updates. A small training-loss reduction alone must not trigger production promotion or repeated tuning against these same two validation clips.

## Verification and next step

Saved weights restored successfully in a separate process, reproducing validation loss **3.839490119148703**. Original checkpoint SHA256 stayed unchanged, the base received no gradients, and only adapter parameters were optimized. Ten new adapter tests cover identity initialization, updates through an actual tiny decoder, frozen weights, optimizer ownership, full targets, evaluation without updates, checkpoint/hash/base identity and label-free generation. The full local suite passed **169 Python tests**. The CPU CI job is configured to exercise the tiny decoder tests; no new remote run is claimed.

The browser continues using its existing baseline. No cloud resources were started. Next, inspect source-video/text alignment and extractor compatibility, expand reviewed training/development data, then run a predeclared experiment. [Aggregate result](small-adapter-training-2026-11-18.json).
