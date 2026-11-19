# Local ML dependencies and setup

Python **3.12**, macOS on Apple silicon. Use the separate `.venv-ml` environment. The application Docker image and camera-app environment are separate.

**Installed and checked on this Mac, 18 November 2026:** all twelve listed distributions import successfully. The pinned SLT checkpoint and detector/pose assets are local; strict model restoration passed. One complete validation-video prediction ran, but differed from its supplied reference and did not pass translation quality. See the [baseline results](local-baseline-results-2026-11-18.md).

| Dependency | Pinned version | Purpose |
|---|---|---|
| torch | 2.9.0 | Model operations and CPU/MPS execution |
| torchvision | 0.24.0 | Compatible upstream model imports |
| transformers | 4.40.0 | mT5 model and tokenizer interface |
| tokenizers | 0.19.1 | Matching Transformers tokenizer runtime |
| sentencepiece | 0.2.0 | mT5 SentencePiece vocabulary |
| numpy | 1.26.4 | Pose arrays and batching |
| av | 19.0.2 | Timestamp-aware video decoding |
| einops | 0.8.1 | Model tensor rearrangement |
| onnxruntime | 1.20.1 | Local detector/pose model execution |
| rtmlib | 0.0.13 | Whole-body pose extraction |
| opencv-python | 4.10.0.84 | Image operations required by RTMLib |
| opencv-contrib-python | 4.10.0.84 | RTMLib also declares this distribution |

Transitive packages are resolved by pip. This is a direct-dependency pin set, not a complete cross-platform lock. Both OpenCV distributions are pinned to the same release to satisfy RTMLib's packaging; do not independently upgrade one. No CUDA, DeepSpeed or TensorFlow is required for the local pose-only experiment.

The [Mac dependency snapshot](../../requirements-ml-macos.lock.txt) additionally pins the **38 installed distributions** in this runtime's dependency tree. It is specific to Mac ARM64/Python 3.12, rather than a Linux GPU lock.

## Install

From `/Users/user/Documents/ChatGPT/Neosignis` in Antigravity:

```sh
sh scripts/setup_ml_macos.sh
```

The setup creates `.venv-ml` if absent and installs [requirements-ml-macos.txt](../../requirements-ml-macos.txt). It can reuse matching system packages, including the already installed PyTorch, while new packages install into the project environment. It does not upgrade system packages. On this Mac the existing pinned PyAV distribution was copied from `.venv-data` to avoid a redundant network transfer.

For an existing ML environment, the dependency command alone is:

```sh
.venv-ml/bin/python -m pip install -r requirements-ml-macos.txt
```

## Acquire model assets

```sh
.venv-ml/bin/python scripts/data/download_unisign_assets.py
.venv-ml/bin/python scripts/data/download_pose_assets.py
```

Assets remain under ignored `data/local/models/unisign/`, with source/tokenizer receipts and checkpoint verification. Downloads do not start training. The SLT checkpoint supplies decoder weights; only mT5 configuration/tokenizer assets are separately acquired. Complete architecture matching is required before loading, so missing weights cannot silently stay random.

If the original pose-model host is slow, `download_pose_assets.py --mirror` uses the extractor maintainer's public mirror, pinned to its resolved revision. That was the successful acquisition route on this Mac.

## First baseline

```sh
PYTHONPATH=src .venv-ml/bin/python scripts/data/run_asl_baseline.py \
  --archive /Users/user/Downloads/val_rgb_front_clips.zip \
  --inventory data/local/how2sign/research-only/val/front/val_rgb_front_clips.integrity.json \
  --references data/local/how2sign/research-only/val/annotations/how2sign_val.csv \
  --device cpu \
  --output data/local/models/unisign/baseline.json
```

This selects one complete short validation utterance, extracts poses and attempts a model prediction. CPU is the conservative first check on the 8 GB Mac; test MPS separately. Private output includes prediction/reference text and processing times. It does not train, approve ASL accuracy or establish live latency. Training requires its own data split and evaluation.
