# ASL datasets: access and relevance to the MVP

Checked against publisher pages on 17 November 2026. These are candidate sources, not downloaded or training-approved data. This is a source/access review, not a dataset quality audit or a measured model result.

## What a dataset gives us

A dataset is a collection of examples plus descriptions of those examples. A model learns from training examples; separate examples measure whether it works on new people. Clicking a dataset page usually opens documentation, not a ready-to-use interpreter.

- **Video:** watchable signing, used to learn appearance and motion.
- **Labels/annotations:** the sign or sentence meaning, timing, and related metadata.
- **Keypoints:** numerical positions of hands, face and body over time. These need code to load or visualize; they are not ordinary videos.

Individual-sign recognition and sentence translation are different tasks. Recognizing several individual signs does not establish understanding of ASL grammar, negation or conversation. A public recognition dataset also does not automatically supply permission to show a person's footage to users or create their avatar.

## 1. PopSign v1 — a first isolated-sign experiment

**Contains:** mobile-camera videos of individual ASL signs. The publisher lists 250 signs and 47 signers, with a full release around 1.1 TB.

**Role:** a candidate for testing whether our input/preprocessing/model can distinguish selected individual signs across people. Any benefit to later sentence translation must be measured separately. The publisher explicitly says the dataset is not intended for continuous recognition or ASL-to-English translation.

**Access (updated after the user supplied screenshots):** the [official download guide](https://signdata.cc.gatech.edu/view/guides/downloading_popsign/index.html) documents per-sign TAR archives under `https://signdata.cc.gatech.edu/data/<dataset>/<category>/<split>/<sign>.tar`. The documented `popsign_v1_0/game/train/after.tar` example returned HTTP 200 and a 2.10 GB size in a HEAD check; two hello split archives also responded. No archive bodies were downloaded. Check sizes and preserve original files/splits before importing a bounded subset. The [PopSign walkthrough](popsign-download-walkthrough.md) explains the fields and limits. Website previews are resized and speed-adjusted, so use original archive media. Contact the publisher only if the documented route fails or clarification is needed.

**Terms:** published CC BY 4.0. Record attribution and review the intended uses. Our first action is to verify archive availability and inspect a small permitted sample; this does not establish conversational translation.

## 2. ASL Citizen — everyday-camera individual signs

**Contains/role:** isolated ASL recordings designed for recognition/dictionary retrieval. Potentially useful for researching variation across signers and capture conditions; it does not teach full conversation translation.

**Access:** open the [official Microsoft download page](https://www.microsoft.com/en-us/download/details.aspx?id=105253), select **Download**, then choose **ASL_Citizen.zip**. The listed archive is **42.8 GB**. The separate demographics ZIP is not the signing corpus and is not needed for a first technical inspection.

**Terms:** [public terms](https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/) limit use to noncommercial, non-revenue-generating research. Do not assume a startup's internal prototype qualifies. The [project page](https://www.microsoft.com/en-us/research/project/asl-citizen/) gives `ASL_Citizen@microsoft.com` for commercial enquiries. Keep this outside product training unless permission is established.

## 3. How2Sign — continuous signing paired with English

**Contains/role:** more than 80 hours of signed material with English transcripts and additional modalities. Its sentence-level pairs are closer to our eventual ASL-to-English task, though the subject matter and recording setup differ from everyday camera conversations.

**Access:** on the [official page](https://how2sign.github.io/), scroll to **Download**. Video, English references and keypoints are separate downloads. For a permitted small inspection, identify the **Green Screen RGB clips (frontal view)** and **English Translation (manually re-aligned)** sections. Match video IDs/timestamps with the corresponding references; arbitrary files are not interchangeable. The entire training-video downloads are large.

**Terms:** public release is CC BY-NC 4.0, with commercial use excluded. Separate permission is needed for our product route. This is a research/permission enquiry candidate, not a ready commercial training corpus.

## 4. CLERC Épée — motion arrays and annotations

**Contains/role:** keypoint sequences plus English/gloss annotations. Useful for examining movement-based recognition and phrase alignment. Raw signer video is not supplied, including under its advertised commercial licence; it cannot provide our realistic signer identity assets. Its 128-point format also differs from our current 553-point schema and needs a reviewed adapter.

**Access:** open the [Hugging Face dataset card](https://huggingface.co/datasets/CLERC-DATA/epee) to inspect example rows. Open [Files](https://huggingface.co/datasets/CLERC-DATA/epee/tree/main): `metadata.csv` indexes examples, `annotations/` contains descriptions/timing, and `keypoints/` contains `.npy` numerical arrays. The `.npy` files will not play in a video player.

**Terms:** the public release is CC BY-NC-SA 4.0. The [publisher](https://clerc.io/data) advertises separate commercial licensing through `florian@clerc.io`. Request permitted uses, sample scope and pricing before product training. Publisher benchmark percentages do not predict our model's accuracy.

## 5. WLASL — word-level research reference

**Contains/role:** individual signs across a vocabulary of up to 2,000 glosses. Useful as a research comparison, not a sentence-translation corpus.

**Access:** the [official repository](https://github.com/dxli94/WLASL) contains annotations and downloader/preprocessing instructions under `start_kit`. Downloading the GitHub ZIP alone does not obtain all videos. Original links can disappear; the README links a request form for missing/preprocessed videos. Do not execute old download scripts without checking them.

**Terms:** the maintainers explicitly exclude commercial usage. It is not our default product-training source.

## 6. Talksign Marketplace — potential supplier enquiry

The [linked page](https://www.talksign.co/marketplace) presents licensable-data marketing. I have not verified a downloadable catalogue, sample files, a contract or pricing. Treat this as a supplier enquiry: ask for exact language, whole utterances versus isolated signs, signer diversity, annotation samples, and permission to train and distribute a commercial model. Do not count advertised data as acquired data.

## The primary corpus we still need: commissioned ASL

For our own everyday-conversation demo, commission natural complete utterances with reviewed English meanings, alongside selected isolated-sign/negative examples. Examples such as "Please repeat that" describe intended meanings, not English word-order signing instructions. The reviewer must check what the contributor actually signed.

Use the [contributor brief](pilot-contributor-brief.md). Begin with 3–5 adult contributors and 100–200 reviewed utterances to test the collection process. This is not enough to claim broad conversation accuracy; expand the dataset according to measured failures. Agree payment and permissions before recording. Training, playback and avatar/likeness uses require distinct decisions.

## Next steps and review checklist

1. Finish local AWS login and deploy reviewed durable storage following the [setup guide](aws-collection-setup.md). Source/licence enquiries can proceed before AWS is connected.
2. With a fluent Deaf ASL reviewer, freeze a small everyday meaning set and confusing/unsupported examples. Keep the individual-sign diagnostic separate from the full-utterance MVP.
3. Verify PopSign archive sizes/access, inspect CLERC's sample structure and request commercial terms for promising continuous data. Obtain permission before restricted downloads/use; avoid bulk acquisition initially.
4. Agree contributor engagement, then collect/review a small pilot. Preserve pseudonymous signer IDs, actual meaning, source/permission reference, technical metadata, checksum and review state.
5. Approve a dataset version and separate training, tuning and final-test people. Do not tune on the final test set. Keep repeated clips/sessions from leaking across the split.
6. Train a baseline and connect it to the camera input. Test preprocessing, inference and unsupported-input handling; report results by meaning, unseen signer and recording condition, with latency and error examples. Unit tests check software behavior; separate real ASL evaluation checks interpretation quality.

The key review questions are: does it recognize a new person, distinguish confusing meanings, reject unsupported signing, and preserve meaning? Agree numerical acceptance targets with the language reviewer before the final evaluation. No Neosignis accuracy percentage has been measured yet.

I handle acquisition tooling, formatting, storage, training integration and technical checks. The founder coordinates introductions and commercial/participant agreements. Fluent ASL reviewers provide linguistic ground truth. Raw media stays in private working storage/S3, not the code repository. The dataset loader/approval workflow is still pending.

## New lead from the portal: Assistant Phrase ASL v1.0

The [separate data card](https://signdata.cc.gatech.edu/view/datasets/assistant_phrase_v1_0/index.html) describes phrase landmarks/text for controlling a virtual assistant and states CC BY 4.0, but its prominent banner says the dataset has not been released and the actual data is unavailable. Do not count it as acquired/available or apply the PopSign download pattern to it. The publisher also excludes general continuous interpretation as a supported use. It is a release enquiry candidate, not a current dependency. PopSign v2.1 is another separate sidebar entry; its exact release, rights and contents require independent review before selection.

## Acquisition update — 18 November 2026

One PopSign v1.0 game/val/hello archive is now downloaded locally: 925,061,120 bytes, 157 MP4 files. Archive size, structure, hashes and MP4 container headers were checked. No video-decoding, ASL review or training approval is claimed. See the [acquisition summary](popsign-sample-acquisition-2026-11-18.json) and [five-step execution checklist](pilot-execution-checklist.md). Other source bodies remain unacquired. Earlier source-access notes are dated checks, not evidence that the full datasets were downloaded.

## How2Sign acquisition update — 18 November 2026

The original validation English references are downloaded locally (1,741 sentence records), but both frontal and side-view validation video ZIPs are quota-blocked by Google Drive. No How2Sign videos were obtained and commercial permission remains unconfirmed. See [download status and resume steps](how2sign-download-status.md).

## User-provided How2Sign video update — 18 November 2026

The frontal validation ZIP is now available in the user Downloads folder. All 1,739 video members passed archive checks and match original reference IDs; two of the 1,741 reference rows have no video. It is read in place and has not been fully extracted, decoded, linguistically reviewed, uploaded or approved for training. See [the acquisition summary](how2sign-acquisition-2026-11-18.json).
