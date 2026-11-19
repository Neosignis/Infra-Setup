# How2Sign download status

18 November 2026. The founder requested a download. We attempted a bounded validation subset rather than the full release, given roughly 17 GiB of local free space. No cloud resources were created.

## Current update — user download verified

The user downloaded `/Users/user/Downloads/val_rgb_front_clips.zip`. It is 1,778,074,855 bytes. Reading the ZIP in place verified CRCs, safe paths, file hashes and MP4 container headers for **1,739 video clips**. All 1,739 video IDs match the original validation English references. Two of the 1,741 reference rows have no corresponding video; reasons have not been established. No video lacks a reference.

The archive remains in Downloads; it was not copied or fully extracted. One bounded original clip was copied into private project storage for playback. Video decoding, timing/semantic alignment, linguistic quality, signer-disjoint evaluation and commercial/training approval remain unverified. See the [acquisition summary](how2sign-acquisition-2026-11-18.json). Retain the original ZIP until a verified storage copy exists.

## Earlier automated download: references

The original validation English references, `how2sign_val.csv`: **311,131 bytes, 1,741 sentence records**. The file is tab-separated despite its extension. All rows parsed; required sentence/name fields exist and numeric end times follow start times. Source content was not rewritten.

Local folder:

```text
/Users/user/Documents/ChatGPT/Neosignis/data/local/how2sign/research-only/val/annotations/
```

The folder is excluded from Git. Its references are text, not signing footage, and do not by themselves supply training examples for sign-to-text.

## Video access blocked

Both publisher links returned a Google Drive public-download quota-exceeded error:

- [Frontal validation clips](https://drive.google.com/file/d/1DhLH8tIBn9HsTzUJUfsEOGcP4l9EvOiO/view): publisher lists 1.7 GB.
- [Side-view validation clips](https://drive.google.com/file/d/1mxL7kJPNUzJ6zoaqJyxF1Krnjo4F-eQG/view): publisher lists 1.2 GB.

The [manually realigned validation references](https://drive.google.com/file/d/1Vpag7VPfdTCCJSao8Pz14rlPfekRMggI/view) were also not retrievable anonymously; its exact access problem is unverified. The original references were successfully obtained and are a different timing source.

Earlier automatic attempts obtained no video files; the user subsequently supplied the frontal ZIP, verified above. A regular browser download may be worth trying with the publisher link, or access can be retried when Google restores quota. If it remains unavailable, ask the publisher for another authorized distribution route. No signed-in browser cookies were read/exported, sharing permissions changed or quota workarounds attempted. No retry automation was scheduled.

## Scope and rights

[How2Sign's public terms](https://how2sign.github.io/) are CC BY-NC 4.0. Local download/source inspection does not establish commercial training, product playback or likeness rights. No such permission was obtained, no model was trained and no data was uploaded to AWS. A research-only folder name is an organizational label, not an approval system.

The full frontal training sentence clips are listed as 31 GB; original training videos as 290 GB. Neither fits the current local free-space budget. A full-corpus download needs a separate storage decision.

## Resume when access returns

1. Retry the publisher's frontal validation ZIP and retain the original English references. Keep the view and split explicit.
2. Check ZIP completion, file sizes, CRCs, source hashes and safe member paths before extraction. Do not extract an archive merely because it downloaded.
3. Match clip IDs to the original reference rows and separately inspect alignment/decodability. The manually realigned references require their own timing treatment.
4. Retain unreviewed/unapproved status until the required linguistic, rights and split reviews are complete. Publisher validation material used for development must not become our claimed unseen final holdout.

The read-only archive inspector now supports bounded ZIP checking as well as TAR. Seventeen archive regressions and the full 71-test Python suite pass. These tests validate our file-handling code, not video decoding or ASL interpretation quality. The user-provided archive was subsequently checked with the inspector as noted above. See the [machine-readable access evidence](how2sign-access-check-2026-11-18.json).
