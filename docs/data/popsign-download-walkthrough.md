# PopSign: what the download screenshots mean

Verified against the [official guide](https://signdata.cc.gatech.edu/view/guides/downloading_popsign/index.html) on 17 November 2026. Website commands are reference material, not instructions automatically executed by our project.

## The direct download format

```text
https://signdata.cc.gatech.edu/data/<dataset>/<category>/<split>/<sign>.tar
```

The publisher's example is:

```text
https://signdata.cc.gatech.edu/data/popsign_v1_0/game/train/after.tar
```

| Field | Meaning for our work |
|---|---|
| `popsign_v1_0` | Exact release; keep its licence, metadata and files together |
| `game` | The publisher's game category; verify label/variant metadata |
| `train` | Training examples; `val` is for tuning and `test` for final evaluation |
| `after` | The individual sign label; it is the guide's example, not a chosen MVP phrase |
| `.tar` | An archive containing multiple files, not one playable video |

The smallest documented download unit is a sign/category/split archive. The guide does not supply an individual-video download API. A request can still be large; inspect the archive's headers and size first. Do not run the recursive/full-dataset commands for the first sample.

Example header check on macOS, which does not download the archive body:

```sh
curl --fail --location --head \
  'https://signdata.cc.gatech.edu/data/popsign_v1_0/game/train/after.tar'
```

An HTTP success/size check is only an access check. It does not establish that an archive is intact or a model is accurate. A missing size means we need a bounded downloader before fetching the body.

## Verified file sizes (HEAD requests only)

| Archive | HTTP status | Approximate download size |
|---|---|---|
| `game/train/after.tar` | 200 | 2.10 GB |
| `game/val/hello.tar` | 200 | 925 MB |
| `game/test/hello.tar` | 200 | 571 MB |

These are decimal sizes and archive bodies were not downloaded. See [the recorded access check](popsign-access-check-2026-11-17.json). We have verified access, not contents, integrity or linguistic quality. Even a one-sign archive is large; define a download limit before acquisition. An initial diagnostic should preserve final holdout independence rather than tune on a test archive inspected during development.

## Details that matter

- The website's preview grids change video resolution and speed. Use originals from the archives for any approved model experiment.
- The publisher's top-level Datasets page displays an unfinished "Create this Page" template. This is their website content, not a task for us. Specific dataset/sign links can still work.
- `non-game` is not automatically a negative class. A valid variant or another sign is not the same as no signing; inspect/review labels before using it.
- Keep the publisher's splits and pseudonymous participant IDs. Check signer overlap before describing a test as signer-independent; three split folders alone do not prove that.
- Keep v1.0 and v2.1 separate. Do not assume another version has identical terms, vocabulary, split rules or data format.
- Review an archive's member list before extracting. Reject absolute paths, `..` traversal and unsafe links; keep the original archive/checksum and extract into private working storage outside Git tracking.

## Proposed first experiment

Inspect the published entries for [hello](https://signdata.cc.gatech.edu/view/datasets/popsign_v1_0/game/hello/index.html), [please](https://signdata.cc.gatech.edu/view/datasets/popsign_v1_0/game/please/index.html) and [thankyou](https://signdata.cc.gatech.edu/view/datasets/popsign_v1_0/game/thankyou/index.html). We can extend a small vocabulary once sizes, labels, rights and capture compatibility are checked.

Start with a bounded subset, record source/release/category/split, archive hash and permission/attribution evidence, then inspect original clips and participant IDs. Media stays outside Git. Local acquisition does not need AWS; later approved uploads require the [private storage setup](aws-collection-setup.md).

Recognition of these isolated signs is a diagnostic baseline. Full everyday utterances, unsupported-input handling and independent ASL evaluation remain necessary for the intended MVP. At the original guide-writing stage no archives had been downloaded. On 18 November a separate acquisition downloaded game/val/hello only; see the [acquisition summary](popsign-sample-acquisition-2026-11-18.json). No training approval is implied.

## Assistant Phrase ASL is a separate, unavailable lead

The [Assistant Phrase v1.0 card](https://signdata.cc.gatech.edu/view/datasets/assistant_phrase_v1_0/index.html) describes assistant-command phrases in landmark/Parquet form, with text references. It currently carries a prominent notice that the actual dataset has not been released. It also excludes general continuous interpretation as an intended use. A historical release-date field elsewhere on the card does not establish availability.

It may warrant a publisher enquiry, but it is not currently an available source in our plan. The PopSign archive pattern must not be applied to this separate dataset without its own instructions.
