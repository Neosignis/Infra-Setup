# Prepared training-data pilot

18 November 2026. **Real training inputs are prepared.** A subsequent [small adapter experiment](first-local-training.md) completed; it reduced training loss but did not improve validation predictions.

| Prepared item | Count |
|---|---:|
| Training utterances, from distinct source videos | 32 |
| Training pose frames, retained in full | 4,203 |
| Training numeric cache | 5.13 MB |
| Validation clips catalogued | 1,739 |
| Validation videos converted to pose features | 2 |
| Missing validation videos recorded separately | 2 |

## Where to find it

All data stays on this Mac, outside Git:

```text
data/local/prepared/how2sign-pilot-v1/
  train/index.csv        readable training examples and review status
  train/manifest.json    source revisions, English targets, hashes and splits
  train/*.npz            numeric pose sequences and observation masks
  val/index.csv          two validation feature examples
  val/manifest.json      validation source hashes and native timestamps
  val/catalogue.jsonl    all 1,739 matched validation clips
  val/quarantine.json    two annotation rows with missing video
  readiness.json         loader checks and quality-review flags
```

The original video archive remains in Downloads. It was not duplicated or assigned to training. Open `train/index.csv` to inspect the selected utterances; `.npz` files are numerical inputs, not playable signer videos.

## Source and limits

Training poses come from the [Uni-Sign publisher's How2Sign pose release](https://huggingface.co/ZechengLi19/Uni-Sign/tree/eab251b7fe7e8521afc0e67be98add670ea40a0d), using [pinned model-maintainer training annotations](https://github.com/ZechengLi19/Uni-Sign/blob/eed438bcb49e30405cd6ccdfcccca330c134e830/data/How2Sign/labels.train). These are derived annotations, including some joined sentence IDs. The attempted original training CSV download was quota-limited. The upstream label file contains 31,086 entries; **we prepared 32, not the whole training set**.

Only 26,010,639 bytes were transferred from the multipart pose archive, below the 64 MiB limit. Range requests avoided downloading/combining the roughly 8.5 GB archive. Each selected ZIP member passed CRC, then source and numeric hashes were recorded. Whole archive-part SHA256 values are recorded as publisher metadata, **not claimed verified** from partial reads.

Training files preserve every declared source frame, with full English targets and raw pose scores. The publisher's pose files lack timestamps: their frame order is retained and timing is explicitly unknown. Validation features use the existing video loader and preserve real timestamps. No fixed FPS or clip duration is invented, and no targets are truncated at 50 tokens.

No source-video IDs overlap between the 31,086 training labels and our validation annotations. This does **not** prove different signers; signer IDs are unavailable. This pretrained model has already used How2Sign, so this pilot cannot establish performance on new signers or independent everyday conversations.

One nine-frame training clip is flagged for extra completeness/alignment review. Pose visibility is a technical check, not a judgement of ASL correctness. All language/alignment review remains pending. This how-to-domain process pilot is insufficient for the everyday MVP, realistic avatars or text-to-sign.

## Reproduce and consume

From the repository root, with the installed ML environment and checked local validation references:

```sh
PYTHONPATH=src .venv-ml/bin/python scripts/data/prepare_training_pilot.py
PYTHONPATH=src .venv-ml/bin/python scripts/data/prepare_validation_pilot.py
PYTHONPATH=src .venv-ml/bin/python scripts/data/check_prepared_training.py
```

The first command acquires missing small pinned source metadata/labels and resumes verified per-example caches. It refuses to merge a different selection into the same output. Validation preparation refuses an existing completed output; keep the current files and use the checker to revalidate them. Alternate paths/counts are available through `--help`.

`PreparedPoseDataset` loads hash-checked numeric arrays with pickle disabled. It supplies the existing `torch_unisign_collate` and PyTorch `DataLoader`; no extra packages or cloud resources were required. Publisher training splits are required for training usage. Source pickle conversion is restricted to pinned publisher data and a small NumPy allowlist; it is not a general-purpose upload service or security sandbox.

## Next step

The data now supports a small training-process experiment. Before claiming a useful model, expand the training sample, inspect matching source video/text alignment, obtain fluent Deaf ASL review and collect independent everyday messages for evaluation. Keep validation/test examples outside fitting and run a separate evaluation after any training. [Technical results](training-preparation-2026-11-18.json).
