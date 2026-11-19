# Video input readiness and the next engine step

18 November 2026. This is a technical source-media check, not language evaluation, training approval or an inference benchmark.

## Completed

The user-provided How2Sign ZIP was read in place. Its recorded SHA256 was rechecked, then **32 of 1,739 video clips** were selected: shortest and longest reference durations plus a deterministic sample across clip IDs. Every selected clip was decoded fully from the ZIP, with a first-frame RGB24 conversion check. No full extraction, cropping, resampling or training dataset was produced.

- **32/32 sampled clips decoded**, with zero decode failures.
- Sampled dimensions: **1280 × 720**.
- Sampled reported frame rates: **24, 30, 50 and 60 fps**.
- No missing or non-increasing frame timestamps in the sample.
- Across the 1,739 matching reference rows, **240 utterances exceed ten seconds**. Reference durations range from approximately 0.11 to 53.22 seconds. These are reference intervals, not confirmation of linguistic or temporal alignment.

These results apply only to the selected sample. They do not prove that all videos decode, that signing is labelled correctly or that the videos match our target phone conditions. See the [technical summary](how2sign-decode-summary-2026-11-18.json). The detailed per-clip report stays under ignored `data/local/`.

## Immediate design decisions

1. **Use timestamps, not an assumed source frame rate.** Sampling/resampling must be defined by the selected model's actual input requirements. Preserve source timestamps and record every derived transform.
2. **Preserve complete utterances.** The current HTTP contract limits input to ten seconds/300 frames and a 4 MiB body. It is a foundation contract, not a sufficient continuous-video transport. The observed long utterances require a versioned input/session design, model-aware temporal handling and bounded buffering. Do not silently cut every example to ten seconds.
3. **Preserve hands, face and relevant body information.** A crop/resize should follow a model-specific, tested specification rather than arbitrarily squashing a 16:9 source into a square.
4. **Keep development and final evaluation separate.** This is the publisher's validation subset. It is useful for source inspection and development, not a new training corpus or a claimed independent Neosignis final holdout.

## Next implementation

**Later 18 November update:** the [variable-length loader](training-loader.md) is now implemented and Uni-Sign How2Sign pose-only is [selected for research](../recognition-model-decision.md). Its model-specific extractor/adapter is still pending. The probe itself did not install or evaluate a model; the paragraph below records the earlier next-step assessment.

The next engine package is the **versioned model-input/preprocessing adapter**: read frames, respect timestamps/orientation, apply the chosen extractor or RGB preprocessing, preserve missing-observation masks, and produce the exact model input. That depends on choosing a model with suitable code/weight/data rights and documented runtime requirements. No model is selected or installed by this probe.

After that, implement the real recognition provider, connect live camera input and evaluate sign-to-text on separately held-out signers. The MVP also requires submitted-text-to-reviewed-ASL output, responsive live sessions and actual phone/desktop testing. Decode success does not enable either translation direction.

Fluent ASL review, a supported utterance scope, usable training data and signed-output assets remain dependencies. How2Sign's noncommercial public terms are unchanged; no commercial permission or training approval was obtained. No AWS upload was performed.

## Run locally in Antigravity

A separate ignored `.venv-data` environment has been created with the pinned decoder. The application environment and running camera app were not replaced.

For another checkout, use a consistent Python 3.12 installation:

```sh
python3 -m venv .venv-data
.venv-data/bin/python -m pip install -r requirements-data.txt
```

From this repository root:

```sh
.venv-data/bin/python scripts/data/probe_how2sign.py \
  --archive /Users/user/Downloads/val_rgb_front_clips.zip \
  --inventory data/local/how2sign/research-only/val/front/val_rgb_front_clips.integrity.json \
  --references data/local/how2sign/research-only/val/annotations/how2sign_val.csv \
  --sample-size 32 \
  --output data/local/how2sign/research-only/val/front/decode-probe.json
```

The inventory and references are local acquisition files, not Git assets; obtain and inspect the same source before using this command on another computer. The probe verifies the recorded archive hash and each selected clip hash. It bounds clip bytes and frame counts, forces MP4/MOV parsing and disables external data references. The source ZIP remains unchanged.

Tests for this tool:

```sh
.venv-data/bin/python -m unittest discover -s tests -p test_video_probe.py -v
```

The main CI test job installs `requirements-data.txt` to exercise the real decoder tests. Synthetic video fixtures verify mechanics only; they are not ASL training data. No new remote CI run is claimed until these local changes are published.
