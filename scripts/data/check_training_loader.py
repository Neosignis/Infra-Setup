"""Exercise whole-video loading without extracting poses, fitting a model or uploading data."""
import argparse
import json
from pathlib import Path

from neosignis.training.how2sign import How2SignArchive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--references', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sample-size', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.sample_size <= 32:
        parser.error('Sample size must be 1..32')
    if args.output.resolve() in {p.resolve() for p in (args.archive, args.inventory, args.references)}:
        parser.error('Output cannot overwrite source input')
    source = How2SignArchive(args.archive, args.inventory, args.references, split='val')
    ordered = sorted(range(len(source)), key=lambda i: source.records[i].reference_end_s - source.records[i].reference_start_s)
    selected = list(dict.fromkeys([ordered[0]] + list(reversed(ordered))))[:args.sample_size]
    results = []
    for index in selected:
        count, last = 0, None
        for timestamp, _frame in source.iter_frames(index):
            count += 1
            last = timestamp
        clip = source.records[index]
        results.append({'reference_duration_s': clip.reference_end_s - clip.reference_start_s,
                        'decoded_frames': count, 'last_frame_relative_pts_ms': last,
                        'full_clip_completed': True})
    result = {'schema_version': 'neosignis.loader-check.v1', 'archive_sha256': source.archive_sha256,
              'references_sha256': source.references_sha256, 'publisher_split': source.split,
              'matched_clips': len(source), 'missing_video_rows': len(source.missing_video_ids),
              'unreferenced_videos': len(source.unreferenced_video_ids), 'checked_clips': results,
              'all_clips_decoded': len(results) == len(source), 'model_features_extracted': False,
              'training_run': False, 'recognition_accuracy_measured': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
