# Matching source videos and ASL review packet

19 November 2026. Downloaded the **eight exact training RGB clips** from the pinned Uni-Sign publisher mirror and built side-by-side source/pose review videos. Original labels, numeric training poses and model weights were not changed.

## Open the review

Local directory, excluded from Git:

```text
data/local/reviews/asl-adapter-pilot-2026-11-19/
  review.html           offline video review and notes export
  review-sheet.csv      editable review worksheet
  contact-sheet.jpg     eight visual examples at a glance
  source-clips/         original publisher MP4s, byte-preserved
  overlays/             synchronized source/pose videos and JPEG thumbnails
  review-manifest.json  source/pose hashes and diagnostic measurements
  acquisition.json      source revision, archive members and transfer receipt
```

A portable ZIP is alongside that directory, named `asl-adapter-pilot-2026-11-19-review.zip`. Extract the entire ZIP, then open `review.html` in Chrome or Edge. Keep its folders together. The page needs no server or network connection. Notes remain in the page until exported; download the review JSON before closing or refreshing.

Watch each clip before revealing its supplied English reference. Record an independent interpretation, then assess meaning and pose/timing separately. The reference for `1UE7-4mORi0_8-5-rgb_front` is flagged for priority review. No proposed correction has been invented.

## Technical findings

- All **8/8 source videos match their stored pose frame counts**, with 750 decoded frames in total. Stored frame indices cover every source frame exactly.
- All eight derived review videos preserve source frame count and decoded frame timestamps. The original source files retain their recorded hashes.
- Compared five frames per clip—**40 sampled frames**—with our current hash-checked RTMPose extractor. No large spatial-disagreement flag was triggered by the proposed, uncalibrated engineering threshold. These are comparisons between two pose estimates, not human-labelled pose accuracy.
- Source media totals **2,485,112 bytes**. Archive range/index transfer was **13,021,403 bytes**, below the 24 MiB ceiling. No complete multipart archive was downloaded or merged. Whole-part publisher hashes were recorded but not verified from partial reads.
- Browser checks covered actual MP4 playback, caption reveal, exact review-note JSON export, no external requests and a narrow viewport without horizontal overflow. All 178 local Python tests passed, including nine new tests for diagnostics, timing preservation, source-byte preservation, mismatch flags, safe text rendering, checked local reuse and ZIP contents/CRC.

**Meaning and full temporal alignment remain pending human review.** Matching filenames/counts and sampled spatial agreement do not prove sentence boundaries, correct English annotations or ASL comprehension. A fluent Deaf ASL reviewer is needed before approved corrections or a new model-quality claim.

## Reproduce

```sh
PYTHONPATH=src .venv-ml/bin/python scripts/data/prepare_alignment_review.py
```

The default output already exists. Use the current packet, or provide `--output` pointing to a new directory. The script reuses checked acquisition files, refuses changed source copies and avoids overwriting completed reviews. It uses the existing installed Mac ML dependencies. No AWS resources, additional fitting or browser-model promotion were started.

Pinned publisher release: [Uni-Sign source files](https://huggingface.co/ZechengLi19/Uni-Sign/tree/eab251b7fe7e8521afc0e67be98add670ea40a0d). [Aggregate measurements](source-video-review-2026-11-19.json).
