# Pose adapter and local training readiness

18 November 2026. **Preparation can run on this Mac. Substantial Uni-Sign fine-tuning is better planned on a cloud GPU, subject to an actual model benchmark and cost approval.** No paid resources were created.

## Verified on the Mac

The machine reports `MacBookAir10,1`, ARM64 and **8 GB shared physical memory**. PyTorch 2.9.0 supports MPS in an unrestricted local process. A tiny synthetic forward/backward/optimizer step passed on MPS. This verifies basic GPU computation, not Uni-Sign capacity, operator compatibility or ASL training performance. The [compute report](mac-compute-check-2026-11-18.json) records the check. MPS was unavailable inside the restricted process, so the successful check required ordinary host access.

Use the Mac for source inspection, small feature-extraction trials, adapter/unit tests and tiny optimization experiments. Full-model fine-tuning also needs optimizer states, activations and space for checkpoints; an 8 GB shared-memory machine has limited headroom. Do not treat the 1.19 GB checkpoint download size as required training memory. Measure the real model before choosing batch size or cloud instance.

## Implemented now

- [Pose adapter](../../src/neosignis/training/pose.py): versioned 133-point x/y/confidence input, BGR frame conversion and pixel normalization; explicit missing-person handling and rejection of ambiguous multiple-person frames.
- Body/hand/face branch conversion and utterance-wide body normalization; thresholded missing joints remain distinct from temporal padding. Variable-length model batches retain complete sequences and use repeated boundary frames with attention masks. No MediaPipe-to-RTMPose relabelling.
- [Checkpoint validation](../../src/neosignis/training/checkpoint.py): expected byte count and SHA256, CPU tensor-only loading, finite-weight checks and architecture key/shape verification before restoration. No unrestricted pickle fallback or automatic code download.
- **16 new tests**, including hand/face indexing, numerical normalization, low-confidence outliers, missing frames, 1,704-frame batches and real tensor-checkpoint round trips. These use synthetic poses/weights; they do not measure recognition.

The adapter is an independent implementation reviewed against source revision `eed438bcb49e30405cd6ccdfcccca330c134e830`. Actual RTMPose/checkpoint parity remains unverified. [Reviewed input source](https://github.com/ZechengLi19/Uni-Sign/blob/eed438bcb49e30405cd6ccdfcccca330c134e830/datasets.py)

## Before the first ASL training run

1. Resolve upstream code permission. No explicit licence was found in the Uni-Sign repository; public availability does not establish reuse permission. Weight and dataset noncommercial terms remain separate. No upstream code was vendored or executed.
2. Install reviewed extractor/model dependencies and obtain pinned local detector, pose, decoder and SLT assets. RTMLib, ONNX Runtime, Transformers and SentencePiece are currently absent in the checked environment; Uni-Sign weights remain undownloaded. The extractor wrapper needs a real predictor supplied by the caller.
3. Obtain a permitted **training split** or reviewed own recordings. Preserve current validation data. Investigate the recorded 53.22-second-reference/70.96-second-video mismatch.
4. Test the actual forward/backward pass on a tiny training batch, with full text targets. Upstream's model forward caps targets at 50 tokens; our collator does not remove that model-side behavior. A reviewed runtime adapter must change and test it. [Reviewed model source](https://github.com/ZechengLi19/Uni-Sign/blob/eed438bcb49e30405cd6ccdfcccca330c134e830/models.py)
5. Measure peak memory and time per step. Start a small bounded run, validate on held-out data and review ASL meaning before scaling. No defensible full-training duration or accuracy estimate exists yet.

The normalization uses the whole utterance and therefore future frames. It is appropriate for offline inputs; it does not establish causal live streaming. Long-sequence speed, MPS operator support, recognition-provider/browser integration and text-to-sign remain unfinished.

## Reproduce the compute check

In an environment with PyTorch 2.9.0 installed, from the repository root:

```sh
PYTHONPATH=src python scripts/data/check_mac_training.py \
  --device mps \
  --output data/local/mac-compute-check.json
```

Run outside a restricted process if MPS cannot be detected. `--device cpu` explicitly tests CPU instead. For input/checkpoint tests, install `requirements-data.txt` plus PyTorch, then run `PYTHONPATH=src python -m unittest discover -s tests -p 'test_training_*.py' -v`. No code or weights are downloaded by these commands.
