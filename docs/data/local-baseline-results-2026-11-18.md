# First local ASL baseline: 18 November 2026

**The pipeline runs end to end. Translation quality and real-time readiness have not passed.** No ASL training or AWS deployment was performed.

## Completed

- All twelve direct dependencies are installed and import successfully in `.venv-ml`. [Dependency check](ml-dependency-check-2026-11-18.json), [install guide](ml-dependencies-and-setup.md).
- **126 local Python tests pass**, including 46 ML input/asset/runtime tests in the complete suite. Repository/OpenAPI/shell checks also pass. No remote CI result is claimed for these local changes.
- Pinned model source and tokenizer/config files are under ignored `data/local/models/unisign/`. The SLT checkpoint passed exact byte count/SHA256 and tensor-only loading. [Checkpoint check](unisign-checkpoint-check-2026-11-18.json).
- Model construction and complete architecture/state restoration passed on CPU: **587,747,368 parameters**. [Load check](unisign-model-load-2026-11-18.json). No second decoder-weight download was needed.
- Independent pose normalization matched the pinned upstream conversion functions on four synthetic cases, including raw scores above one and missing frames: maximum absolute difference about **1.2 × 10⁻⁷**. This is numerical input parity, not an accuracy score. [Parity check](pose-numerical-parity-2026-11-18.json).

## One real validation clip

The run retained **82 frames**, with a final source timestamp of **3.375 seconds**. Its dataset reference interval is approximately 3.38 seconds. These durations do not by themselves establish semantic alignment.

| CPU stage | Measured elapsed time |
|---|---:|
| Pose extraction, including complete clip decoding | 24.434 s |
| Model preparation/loading | 18.788 s |
| English text generation | 5.052 s |

These are measurements from one unoptimized local run, not P50/P95 or a general performance benchmark. The full source-reference-prediction record remains in private `data/local/models/unisign/baseline.json`.

The prediction differs materially from the supplied English reference. No fluent ASL reviewer has adjudicated the signing/reference/prediction alignment. This example therefore **does not pass a semantic quality gate**, and the CPU timing does not meet the live MVP goal. Successful model execution must not be presented as successful interpretation.

## Integration fixes made

RTMPose emits finite **raw SimCC scores**, which can exceed one or be negative; they are not probabilities. The versioned input is now `neosignis.coco133.xys.v2`. Raw values are preserved, with the checkpoint's threshold/clipping applied at conversion. New tests cover the observed behavior.

The detector is explicitly checked before pose estimation. No detected person stays missing rather than invoking RTMLib's implicit full-image pose fallback. Multiple people require tracking and are rejected by this single-signer baseline.

The offline runtime implements full-text training loss directly, avoiding upstream's 50-token target cap. Only synthetic backward tests have run; no model parameters have been trained on ASL. The running browser/API is unchanged and does not yet use this runtime.

## Next experiment

Review this signing/reference pair, then evaluate a small reviewed set with diverse signers and negatives. Compare actual pose preprocessing and model outputs before choosing fine-tuning settings. Collect permitted training examples separately from these validation clips. Profile GPU execution and end-to-end latency after correctness checks; do not assume fine-tuning alone fixes CPU speed.
