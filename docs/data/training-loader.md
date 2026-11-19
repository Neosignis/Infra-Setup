# Variable-length utterance loader

**Follow-on implementation:** the [pose-input adapter and checkpoint validator](pose-adapter-and-local-training.md) are now implemented. They have synthetic numerical/tensor tests; real extractor/checkpoint integration remains pending.

18 November 2026. Offline loader implemented; no training or ASL feature extraction has run.

## Implemented

- [How2Sign input](../../src/neosignis/training/how2sign.py): read checked ZIP members lazily, match sentence IDs, preserve publisher splits and decode every frame at native timestamps. CSV START/END describe the original recording; they are not applied again as offsets inside sentence clips.
- [Batching](../../src/neosignis/training/utterances.py): preserve full text, pad different feature lengths, return lengths/timestamps/frame masks, and distinguish missing observations from padding. Optional target encoding produces loss labels padded with `-100`. Supply the model's frozen tokenizer with truncation disabled and correct special tokens.
- Length buckets include every example once and budget for padded frames. No random frame subsampling, replacement examples, `drop_last` or silent truncation.
- Explicit configurable defaults: 64 MiB compressed clip, 120 seconds of source timestamps, 7,200 frames, 64 MiB estimated feature-array working storage; batches allow 7,200 padded frames and 256 MiB estimated array storage. A bound failure rejects the complete example. These estimates do not bound total process memory.
- An injected versioned extractor processes one frame at a time. No full RGB sequence is buffered, and no poses or translations are fabricated. Source files are unchanged; no extraction, automatic cropping, resampling, mirroring or pose-pickle loading occurs.

Training usage requires the publisher training split and an external approval record. This is an application guard, not proof of rights. Current validation data remain inspection/development inputs.

## Run locally in Antigravity

From the repository root:

```sh
.venv-data/bin/python -m pip install -r requirements-data.txt
PYTHONPATH=src .venv-data/bin/python scripts/data/check_training_loader.py \
  --archive /Users/user/Downloads/val_rgb_front_clips.zip \
  --inventory data/local/how2sign/research-only/val/front/val_rgb_front_clips.integrity.json \
  --references data/local/how2sign/research-only/val/annotations/how2sign_val.csv \
  --sample-size 4 \
  --output data/local/how2sign/research-only/val/front/loader-check.json
```

The [completed check](training-loader-check-2026-11-18.json) fully decoded four real clips. One contains **1,704 frames spanning about 70.96 seconds**, although its reference interval is 53.22 seconds. Investigate alignment before supervising on that pair. The check does not establish alignment or decode success for all 1,739 clips; two reference rows lack videos.

## Training integration

`FeatureDataset(source, extractor, feature_schema=..., extractor_version=...)` provides PyTorch-compatible `__len__`/`__getitem__`. The extractor receives an AV frame and returns a flat float feature vector plus a boolean observation mask. `torch_collate_utterances` converts arrays to tensors; `functools.partial` can supply target encoding and budgets.

`LengthBucketSampler(lengths, ...)` is a DataLoader `batch_sampler`. Use actual feature lengths from a checked extraction pass/cache, not duration multiplied by assumed FPS. Call `set_epoch(epoch)` for reproducible epochs. Start with `num_workers=0`; spawned workers require picklable, correctly initialized extractors.

The selected model adapter must consume the masks and lengths, apply the correct target loss masking and produce Uni-Sign's exact pose normalization/input layout. The neutral feature matrix is **not** already a Uni-Sign input. No CTC gloss labels are invented from English sentences.

Tests:

```sh
PYTHONPATH=src .venv-data/bin/python -m unittest discover -s tests -p test_training_loader.py -v
```

The PyTorch adapter test skips if torch is absent. The dedicated CI job installs CPU PyTorch 2.9.0 and exercises it. Dependencies are separate from the application image.

## Remaining

See the [model decision](../recognition-model-decision.md). Asset approval/download, pose extraction and checkpoint integration, permitted training data, independent signer evaluation and fluent ASL review remain. No accuracy or live latency has been measured. The public API's ten-second/300-frame contract is unchanged; versioned live transport and text-to-sign remain separate work.
