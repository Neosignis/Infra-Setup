"""Acquire exact training RGB clips and build an offline human-review packet."""
import argparse
import csv
import html
import json
from pathlib import Path
import urllib.request
from zipfile import ZipFile

from neosignis.training.alignment import make_review_video
from neosignis.training.how2sign import sha256_file
from neosignis.training.pose import load_local_pose_extractor
from neosignis.training.prepared import PreparedPoseDataset
from neosignis.training.remote_zip import MultipartRangeReader

REPO = 'ZechengLi19/Uni-Sign'
REVISION = 'eab251b7fe7e8521afc0e67be98add670ea40a0d'


def bundle_packet(root, records):
    """Include declared review artifacts only; do not copy unrelated user files."""
    root = Path(root).resolve()
    destination = root.parent / (root.name + '-review.zip')
    if destination.exists(): raise ValueError('Review ZIP already exists')
    names = {'README.txt', 'review.html', 'review-sheet.csv', 'contact-sheet.jpg', 'review-manifest.json', 'acquisition.json'}
    for record in records:
        names.update([record['source_video'], record['review_video'], record['thumbnail']])
    for name in names:
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing or unsafe declared review artifact')
    with ZipFile(destination, 'w') as archive:
        for name in sorted(names): archive.write(root / name, arcname=root.name + '/' + name)
    with ZipFile(destination) as archive:
        if archive.testzip() is not None: raise ValueError('Review bundle CRC check failed')
    return {'path': str(destination), 'bytes': destination.stat().st_size, 'sha256': sha256_file(destination),
            'files': len(names), 'zip_crc_checked': True}


def finish_packet(root, records):
    import cv2
    import numpy as np
    root = Path(root)
    if not (root / 'README.txt').exists():
        (root / 'README.txt').write_text('''NEOSIGNIS ASL REVIEW PACKET
Extract the entire ZIP, then open review.html in Chrome or Edge.
Keep source-clips/ and overlays/ beside the HTML file. No server is needed.
Left video: unchanged source. Right video: stored pose paired by source frame index.
Check signing before revealing the supplied English reference. Fluent Deaf ASL
review is needed for meaning approval; technical frame checks are not language review.
Export your notes before closing or refreshing: entries are not saved or uploaded.
No training labels or model weights have been changed by this packet.
''')
    cards = []
    for index, record in enumerate(records, 1):
        image = cv2.imread(str(root / record['thumbnail']))
        if image is None: raise ValueError('Unreadable review thumbnail')
        scale = min(620 / image.shape[1], 470 / image.shape[0])
        resized = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)))
        card = np.full((510, 640, 3), 245, dtype=np.uint8)
        cv2.putText(card, f'{index}. {record["id"]}', (10, 22), cv2.FONT_HERSHEY_SIMPLEX, .45, (35, 60, 50), 1, cv2.LINE_AA)
        x = (640 - resized.shape[1]) // 2
        card[32:32 + resized.shape[0], x:x + resized.shape[1]] = resized
        cards.append(card)
    if len(cards) % 2: cards.append(np.full_like(cards[0], 245))
    rows = [np.concatenate(cards[index:index + 2], axis=1) for index in range(0, len(cards), 2)]
    cv2.imwrite(str(root / 'contact-sheet.jpg'), np.concatenate(rows, axis=0))
    bundle = bundle_packet(root, records)
    (root / 'bundle-info.json').write_text(json.dumps(bundle, indent=2) + '\n')
    return bundle


def download_sources(run, root):
    receipt_path = root / 'acquisition.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if (receipt['repo'] != REPO or receipt['revision'] != REVISION
                or {r['id'] for r in receipt['clips']} != set(run['training_ids'])
                or len(receipt['clips']) != len(run['training_ids'])):
            raise ValueError('Existing acquisition belongs to a different source selection')
        for record in receipt['clips']:
            expected = f'source-clips/{record["id"]}.mp4'
            if record['path'] != expected or sha256_file(root / expected) != record['sha256']:
                raise ValueError('Existing source clip differs from acquisition receipt')
        return receipt
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true', timeout=45) as response:
        data = response.read(2 * 1024**2 + 1)
    if len(data) > 2 * 1024**2:
        raise ValueError('Publisher metadata exceeds bound')
    metadata = json.loads(data)
    if metadata['sha'] != REVISION: raise ValueError('Unexpected publisher revision')
    parts = sorted([p for p in metadata['siblings'] if p['rfilename'].startswith('how2sign_rgb_format.zip.')], key=lambda p: p['rfilename'])
    if [p['rfilename'] for p in parts] != [f'how2sign_rgb_format.zip.a{letter}' for letter in 'abcde']:
        raise ValueError('Unexpected RGB multipart layout')
    urls = [{'size': p['size'], 'url': f'https://huggingface.co/{REPO}/resolve/{REVISION}/{p["rfilename"]}'} for p in parts]
    (root / 'source-clips').mkdir(parents=True, exist_ok=True, mode=0o700)
    clips = []
    with MultipartRangeReader(urls, budget_bytes=24 * 1024**2, block_bytes=512 * 1024) as reader:
        with ZipFile(reader) as archive:
            for id_ in run['training_ids']:
                member = f'crop_train/{id_}.mp4'
                entry = archive.getinfo(member)
                if entry.flag_bits & 1 or not 0 < entry.file_size <= 8 * 1024**2:
                    raise ValueError('Unexpected source clip size or encoding')
                payload = archive.read(entry)
                path = root / 'source-clips' / f'{id_}.mp4'
                if path.is_symlink() or (path.exists() and path.read_bytes() != payload):
                    raise ValueError('Refusing to overwrite a different source copy')
                if not path.exists(): path.write_bytes(payload)
                clips.append({'id': id_, 'member': member, 'path': str(path.relative_to(root)),
                              'bytes': len(payload), 'sha256': sha256_file(path), 'zip_crc32': entry.CRC})
                print(json.dumps({'downloaded': len(clips), 'total': len(run['training_ids']), 'transfer_bytes': reader.transferred}), flush=True)
        receipt = {'schema_version': 'neosignis.matching-rgb-acquisition.v1', 'repo': REPO, 'revision': REVISION,
                   'source_parts': parts, 'clips': clips, 'transfer_bytes': reader.transferred, 'transfer_limit_bytes': reader.budget,
                   'whole_part_sha256_verified': False, 'whole_parts_downloaded': False,
                   'linguistic_review_completed': False, 'labels_changed': False, 'training_run': False}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def write_review_page(path, records):
    """Offline HTML with no network calls. Reviewer entries export to JSON."""
    cards = []
    for index, record in enumerate(records, 1):
        id_, reference = html.escape(record['id']), html.escape(record['reference'])
        flags = ', '.join(record['review_flags']) or 'No automatic flag; human review still pending'
        cards.append(f'''<article data-id="{id_}"><h2>{index}. <code>{id_}</code></h2>
<p class="meta">{record['technical']['frames']} video frames · {record['technical']['pose_frames']} stored pose frames · {html.escape(flags)}</p>
<video controls preload="none" playsinline poster="{html.escape(record['thumbnail'])}" src="{html.escape(record['review_video'])}"></video>
<p class="meta">Left: source · Right: stored pose, paired by frame index. Coloured joints are visibility markers, not semantic confidence.</p>
<label>Your interpretation before reading the reference<textarea class="interpretation" rows="2"></textarea></label>
<details><summary>Show supplied English reference</summary><p class="reference">{reference}</p></details>
<div class="fields"><label>Meaning review<select class="decision"><option value="pending">Pending</option><option value="meaning_matches">Meaning matches</option><option value="meaning_differs">Meaning differs</option><option value="unclear">Unclear</option><option value="incomplete">Incomplete utterance</option></select></label>
<label>Pose/timing review<select class="alignment"><option value="pending">Pending</option><option value="appears_aligned">Appears aligned</option><option value="offset_or_wrong_crop">Offset / wrong crop</option><option value="tracking_problem">Tracking problem</option><option value="unclear">Unclear</option></select></label></div>
<label>Notes / proposed corrected English (do not guess)<textarea class="notes" rows="2"></textarea></label>
<a href="{html.escape(record['source_video'])}">Open unchanged source video</a></article>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Neosignis · ASL training review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f1;color:#203a32;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:30px 22px}h1{font-size:32px;margin-bottom:8px}h2{font-size:19px;overflow-wrap:anywhere}code{font-size:.85em}.intro,article{background:white;padding:24px;border:1px solid #dbe3d6;border-radius:12px;margin-bottom:24px}.notice{border-left:4px solid #c49b48;padding-left:16px}.meta{color:#53684e;font-size:14px}video{display:block;width:100%;max-height:700px;background:#142b23;border-radius:8px}label{display:block;margin:14px 0 6px;font-weight:600}textarea,input,select{display:block;width:100%;padding:10px;font:inherit;border:1px solid #becdbd;border-radius:6px;background:#fbfcfa;color:#203a32}textarea{resize:vertical}details{margin:18px 0;padding:12px;background:#f1f5ee;border-radius:7px}summary{cursor:pointer}.reference{font-size:18px}.fields{display:grid;grid-template-columns:1fr 1fr;gap:18px}button{padding:12px 18px;background:#254d3b;color:white;border:0;border-radius:7px;font:inherit;cursor:pointer}a{color:#315d46}footer{margin:24px 0;font-size:14px}@media(max-width:600px){main{padding:18px 10px}.intro,article{padding:16px}.fields{grid-template-columns:1fr}h1{font-size:26px}}
</style><main><h1>ASL training review</h1><p>Eight exact examples from the first local adapter experiment.</p>
<section class="intro"><p class="notice"><strong>Review pending.</strong> Frame-count and pose diagnostics do not establish ASL meaning. No English labels or model weights have been changed.</p>
<ol><li>Watch the signing before revealing the English reference.</li><li>Write your interpretation, then compare meanings. Fluent Deaf ASL review is needed for language approval.</li><li>Check whether the stored points follow the same hands, face and body throughout the clip.</li><li>Export your notes before closing or refreshing. This page does not save or upload entries.</li></ol>
<label>Reviewer code (no contact details)<input id="reviewer" autocomplete="off" placeholder="e.g. reviewer-01"></label><button id="export">Download review notes JSON</button></section>
''' + ''.join(cards) + '''<footer>Original clips are preserved separately. Overlay videos retain source frame order and timestamps; they are visual diagnostics, not corrected training data.</footer>
<script>document.getElementById('export').addEventListener('click',()=>{const notes={schema_version:'neosignis.human-asl-review.v1',reviewer_code:document.getElementById('reviewer').value,created_at:new Date().toISOString(),automatic_training_promotion:false,records:[...document.querySelectorAll('article')].map(a=>({id:a.dataset.id,interpretation:a.querySelector('.interpretation').value,meaning_review:a.querySelector('.decision').value,pose_review:a.querySelector('.alignment').value,notes:a.querySelector('.notes').value}))};const url=URL.createObjectURL(new Blob([JSON.stringify(notes,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='neosignis-asl-review-notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});</script></main></html>'''
    Path(path).write_text(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path('data/local/runs/asl-adapter-pilot-2026-11-18'))
    parser.add_argument('--data-root', type=Path, default=Path('data/local/prepared/how2sign-pilot-v1/train'))
    parser.add_argument('--model-root', type=Path, default=Path('data/local/models/unisign'))
    parser.add_argument('--output', type=Path, default=Path('data/local/reviews/asl-adapter-pilot-2026-11-19'))
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.data_root.resolve()) or args.output.resolve().is_relative_to(args.model_root.resolve()):
        parser.error('Keep review derivatives outside source data and model assets')
    if (args.output / 'review-manifest.json').exists(): parser.error('Review already built; use existing review.html or select a new output')
    run = json.loads((args.run_dir / 'config.json').read_text())
    if sha256_file(args.data_root / 'manifest.json') != run['train_manifest_sha256']:
        raise ValueError('Prepared training data changed after the recorded experiment')
    dataset = PreparedPoseDataset(args.data_root, split='train')
    by_id = {record['id']: index for index, record in enumerate(dataset.records)}
    if not all(id_ in by_id for id_ in run['training_ids']): raise ValueError('Missing training example')
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    acquisition = download_sources(run, args.output)
    sources = {record['id']: record for record in acquisition['clips']}
    extractor = load_local_pose_extractor(args.model_root)
    records = []
    for n, id_ in enumerate(run['training_ids'], 1):
        sample = dataset[by_id[id_]]
        result = make_review_video(args.output / sources[id_]['path'], sample,
                                   args.output / 'overlays' / f'{id_}.mp4', extractor=extractor)
        flags = list(result['engineering_review_flags'])
        if id_ == '1UE7-4mORi0_8-5-rgb_front': flags.append('priority_caption_review')
        record = {'id': id_, 'reference': sample.text, 'reference_status': 'unreviewed_publisher_annotation',
                  'source_video': sources[id_]['path'], 'source_video_sha256': sources[id_]['sha256'],
                  'numeric_pose_sha256': dataset.records[by_id[id_]]['numeric']['sha256'],
                  'review_video': str(Path(result['review_video']).relative_to(args.output)),
                  'thumbnail': str(Path(result['thumbnail']).relative_to(args.output)),
                  'review_video_sha256': sha256_file(result['review_video']), 'review_flags': flags,
                  'technical': result, 'linguistic_review': 'pending', 'suggested_correction': None}
        result['review_video'], result['thumbnail'] = record['review_video'], record['thumbnail']
        records.append(record)
        print(json.dumps({'review_built': n, 'total': len(run['training_ids']), 'video_frames': result['frames'],
                          'pose_frames': result['pose_frames'], 'flags': flags}), flush=True)
    manifest = {'schema_version': 'neosignis.asl-alignment-review.v1', 'source_revision': REVISION,
                'training_config_sha256': sha256_file(args.run_dir / 'config.json'),
                'train_manifest_sha256': run['train_manifest_sha256'], 'records': records,
                'labels_changed': False, 'training_run': False, 'linguistic_review_completed': False,
                'source_timing_preserved_in_derivatives': True, 'pose_timestamps_known': False,
                'original_source_bytes': sum(record['bytes'] for record in acquisition['clips']),
                'transfer_bytes': acquisition['transfer_bytes']}
    (args.output / 'review-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    write_review_page(args.output / 'review.html', records)
    with (args.output / 'review-sheet.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['id', 'supplied_english_reference', 'video_frames', 'pose_frames', 'technical_flags',
                         'source_video', 'overlay_video', 'reviewer_code', 'meaning_review', 'pose_review', 'corrected_english', 'notes'])
        for record in records:
            # Preserve raw IDs in JSON; make CSV cells safe for spreadsheet opening.
            id_cell = "'" + record['id'] if record['id'].startswith(('=', '+', '-', '@')) else record['id']
            text = record['reference']; text = "'" + text if text.startswith(('=', '+', '-', '@')) else text
            writer.writerow([id_cell, text, record['technical']['frames'], record['technical']['pose_frames'],
                             '; '.join(record['review_flags']), record['source_video'], record['review_video'], '', 'pending', 'pending', '', ''])
    bundle = finish_packet(args.output, records)
    print(json.dumps({'status': 'eight_clip_review_packet_ready', 'clips': len(records),
                      'source_bytes': manifest['original_source_bytes'], 'labels_changed': False,
                      'linguistic_review_completed': False, 'review_page': str(args.output / 'review.html'),
                      'bundle': bundle}, indent=2), flush=True)


if __name__ == '__main__': main()
