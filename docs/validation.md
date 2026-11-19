# Validation report

## 19 November: exact RGB source/pose review

- Acquired eight exact `crop_train/` RGB members from pinned publisher revision `eab251b7fe7e8521afc0e67be98add670ea40a0d`, matching the saved experiment's training IDs and unchanged training-manifest hash. Total source bytes: **2,485,112**; bounded archive-range transfer: **13,021,403**. Selected ZIP CRCs and local source hashes checked. Whole-part hashes are not claimed verified.
- Fully decoded **750 source frames**. All eight clips match pose lengths and complete source-frame index coverage. Re-encoded side-by-side review MP4s retain all frames and their relative PTS, verified by decoding the derivatives. Original media files remain byte-preserved.
- Five fresh extractor comparisons per clip, **40 sampled frames**, produced no comparison failures or large spatial-disagreement flags. The threshold is a proposed engineering heuristic; agreement between estimators is not ground-truth accuracy, linguistic alignment or comprehension approval.
- **178/178 local Python tests passed**, including nine new alignment/packet tests. Real synthetic H.264 with irregular PTS checks preserved timing, source bytes and mismatch flagging. Other checks cover visibility/distance math, caption escaping, local hash rejection and a CRC-checked ZIP that includes only declared artifacts. The portable real-data ZIP contains 30 files, **15,436,751 bytes**, SHA256 `259e79fc6a7656dc957693fcdfbd9ac879f1af05fd912c04250cb7523ca7ec86`. Final verification used an isolated temporary bytecode-cache directory after a slow existing Transformers import; no dependency versions were changed.
- Actual Chrome checks passed for MP4 playback, eight review cards, reference reveal, exported JSON contents and mobile horizontal overflow. JavaScript errors: zero; external network requests: zero. Visual review covered the source/pose contact sheet and desktop/mobile layouts. Automated notes were QA fixtures, not ASL reviewer decisions.
- No captions or training features were corrected, no further model fit occurred and no human language review is claimed. [Review instructions and findings](data/source-video-review.md).
## 18 November: first real small adapter fit

- **169/169 local Python tests passed**, including ten new adapter tests. An actual tiny mT5 decoder fixture verifies adapter gradients reduce loss while frozen base tensors remain identical. Tests also cover zero-initialized identity output, optimizer ownership, non-training split rejection, resource-bound selection, full targets, output/source separation, no-update evaluation, tensor-only checkpoint restoration and hash/base identity checks.
- A real CPU experiment completed **32 AdamW updates on eight prepared publisher-training utterances**. The 25,360-parameter residual adapter alone was trainable; all 587,747,368 baseline parameters were frozen in evaluation mode. Only frozen source encoder outputs were cached. The nine-frame flagged example and over-budget examples were excluded before fitting and recorded in the private configuration; sequences/targets were not clipped.
- Token-weighted training cross-entropy: **0.749342 → 0.634852**. Development validation cross-entropy on two examples: **3.806951 → 3.839490**. Both generated validation predictions stayed unchanged and differed from the provided references. No semantic-quality improvement is claimed, and this development set is not an independent signer holdout.
- Saved adapter: **104,157 bytes**, SHA256 `519da47724d5153185f18771eb51e7bbe1da1141d17a0548962464b955001137`. Tensor restoration passed. A separate process loaded the saved adapter against the pinned baseline and reproduced validation loss **3.839490119148703**, with zero optimizer steps. Base checkpoint identity remained unchanged; no frozen base gradients were populated.
- Full experiment time was **45.79 seconds** on CPU; reported peak process RSS on this Mac was 1,896,005,632 bytes. These are local experiment observations, not live-recognition latency or hardware capacity guarantees. No cloud job, browser model replacement, API promotion or new remote CI run occurred. [Training report](data/first-local-training.md).

## 18 November: training-data preparation

- **159/159 local Python tests passed**, including 18 new preparation tests. Checked exact HTTP ranges, transfer ceilings/no full-download fallback, multipart ZIP reading, cache hashes, arbitrary pickle-global rejection, full frame order, missing timing, native validation timestamps, finite/single-signer shapes, joined sentence IDs, train-directory selection, distinct source groups, split misuse, object-array rejection and resuming verified numeric caches without downloading members again.
- Prepared 32 real publisher-training utterances, 4,203 frames, 5,133,526 numeric bytes, from 32 distinct source videos. Publisher pose snapshot `eab251b7fe7e8521afc0e67be98add670ea40a0d`; derived annotations pinned separately to the model's reviewed source revision. The small source annotation file hash is pinned. Range transfer was 26,010,639 bytes, below 64 MiB. Whole-part hashes were not verified; selected member CRCs/source hashes and converted numeric hashes were checked.
- Indexed all 1,739 matching local validation clips and quarantined two missing-video annotation rows. Two complete validation clips produced 25 frames each, last PTS 1,000 ms, through the same hash-checked extractor factory used by the Interpreter. No training/validation reassignment.
- Reopened all 34 numeric files, checked their hashes and collated complete frames and targets. A real PyTorch DataLoader batch of two passed. The same local slow `T5Tokenizer` as the runtime is used, with truncation disabled. One nine-frame source clip is retained and flagged for completeness review. [Aggregate report](data/training-preparation-2026-11-18.json).
- The full training label catalogue and local validation references had zero source-video overlap. Signer IDs, semantic alignment and language quality remain unverified. Training pose timestamps are unavailable; frame order is retained without invented FPS. No optimizer step, loss result, accuracy benchmark, AWS job or new remote CI run is claimed.

## 18 November: browser Interpreter experiment

- **141/141 Python tests passed**, including 15 new activity, video-decode and experimental-service checks. Tests cover movement relative to torso, low visibility, static/short sequences, out-of-scope withholding, no fabricated confidence, real synthetic WebM decode, request-origin/header rules, payload limits, raw-video contracts, admission/cancellation and rejecting purported verified results.
- **37/37 frontend tests passed**. Added label-free submission, unverified/abstention presentation, Studio navigation/detail retention, camera shutdown, typed replies and client output validation. Vitest is configured for one thread worker at a time and direct console output on the 8 GB Mac; temporary dependency diagnostics were restored.
- **8/8 Chrome browser tests passed** using installed Chrome and simulated camera input: three new Interpreter tests plus five Studio tests. Checked actual MediaRecorder WebM bytes (no expected labels), explicit submission, qualified suggestions, mode separation, stopped camera tracks, mobile-width overflow and capture/export integrity. Browser model replies are fixtures; no ASL accuracy is claimed. Screenshots were reviewed, and a clipped desktop camera control was corrected before the final check.
- A real HTTP job used an existing untouched held-out How2Sign clip: 560,001 upload bytes, 82 frames, last PTS 3,375 ms. It reached the model translation stage and returned `abstained / outside_pilot_scope` in **61.22 seconds**, with null candidate, translated text and confidence. [Machine-readable smoke record](data/browser-interpreter-smoke-2026-11-18.json). This establishes integration and output withholding only. It does not validate the activity boundaries, linguistic correctness, everyday coverage or live speed.
- An additional unmocked browser smoke used the user's running Vite proxy and actual local service with simulated-camera WebM. It completed with a framing clarification in **3.2 seconds**, as expected for a test-pattern camera with no usable signer. It supplied no meaning labels. Both smoke timings were observed while other verification work ran; they are not reproducible performance benchmarks.
- No ASL training, text-to-sign model/assets, actual phone evaluation, production provider activation, AWS deployment or new remote CI run occurred.

## 18 November: installed runtime and first video prediction

- **126/126 local Python tests passed** with the application dependencies and installed ML environment available. The ML subset contains 46 tests. Added checks for resumable/hash-verified acquisition, full target loss beyond 50 tokens, output/source separation, raw SimCC scores above one and detector fallback behavior.
- All twelve direct Mac ML dependencies import successfully; the 38-distribution dependency tree is pinned in `requirements-ml-macos.lock.txt`. The camera-app environment was not replaced. [Dependency report](data/ml-dependency-check-2026-11-18.json).
- Checkpoint byte count/SHA256, tensor-only validation and complete architecture restoration passed. Model parameter count is 587,747,368. Independent pose conversion matched pinned upstream functions on four synthetic cases, maximum absolute difference about 1.2e-7. [Baseline findings and reports](data/local-baseline-results-2026-11-18.md).
- One real complete validation video produced a prediction, but it differed materially from the supplied reference. This is not a semantic-quality pass. CPU pose extraction took 24.434 seconds and generation 5.052 seconds for 82 frames spanning 3.375 seconds; no real-time acceptance claim follows.
- Initial integration rejected RTMPose raw scores above one. The input was corrected to preserve finite raw SimCC responses, with source-compatible model threshold/clipping. The feature schema is now `neosignis.coco133.xys.v2`; the old inference API schema is unchanged.
- The existing cancellation/admission test's two-second provider-start wait was flaky on the busy Mac. Startup wait is now ten seconds and the test-provider release bound thirty seconds; the functional cancellation/admission assertions are unchanged. This is not a latency benchmark.
- OpenAPI drift, JSON/Python/Markdown checks, shell syntax and whitespace checks passed. No ASL training, production provider/browser integration, AWS deployment or new remote CI run occurred.

## 18 November follow-on: pose adapter and Mac GPU

- **114/114 local Python tests passed**: 16 new pose/checkpoint tests plus the previous 98. Checked explicit BGR conversion, numeric body/hand/face mapping, low-confidence observations, missing/ambiguous signers, retained long sequences, boundary padding/masks, tensor-only deserialization, pinned bytes/hashes and architecture mismatch rejection. All pose/weight fixtures are synthetic.
- A real MPS synthetic optimizer step passed on the MacBook Air with 8 GB memory, using PyTorch 2.9.0. [Compute report](data/mac-compute-check-2026-11-18.json). This validates only basic GPU operations. No full-model memory, training throughput or ASL benchmark was measured.
- [Pose adapter and training readiness](data/pose-adapter-and-local-training.md) records the upstream revision, absent explicit code licence, model-side target truncation and noncausal normalization. No upstream code was vendored or executed. Extractor/decoder dependencies and weights remain uninstalled/undownloaded in the checked environment.
- CI's dedicated CPU PyTorch job now covers both training test files. Changes remain local; no new remote run or AWS deployment is claimed.

## 18 November: variable-length loader

- **98/98 local Python tests passed**, including **18 new loader tests**. Exercised real synthetic MP4 decoding beyond 10 seconds/300 frames, native/irregular timestamps, feature/missing masks, full-text target encoding and loss padding, padded-memory budgets, split isolation, deterministic length buckets, source integrity and the real PyTorch DataLoader adapter (PyTorch 2.9.0, NumPy 1.26.4, PyAV 19.0.2).
- Four real How2Sign clips fully decoded through the loader, including the longest reference interval: 1,704 frames spanning ~70.96 seconds of source timestamps. Its reference interval is 53.22 seconds; no alignment approval follows from decoding. [Aggregate result](data/training-loader-check-2026-11-18.json).
- OpenAPI drift check, repository syntax/JSON/Markdown checks and whitespace checks passed. No inference contract changes, model/provider installation, feature extraction, training or accuracy benchmark. New CI job is configured but no new remote CI result is claimed.
- Initial full-suite invocation in the system Python lacked the application's FastAPI dependency. The successful full run used the repository application's dependency path plus the installed local decoder/NumPy/PyTorch; it did not replace the running app environment. New data dependencies are pinned separately in `requirements-data.txt`.
- The optional NumPy download into `.venv-data` was cancelled because transfer was slow; that environment still needs the documented `pip install -r requirements-data.txt` step. The successful local tests used the already installed NumPy 1.26.4. No background installation remains running.

Historical validation follows.

Updated 16 November 2026. Re-ran 54 Python tests, 26 frontend tests, TypeScript/production build, OpenAPI drift and repository checks during the architecture review. Browser/container/database/Terraform evidence comes from the linked successful feature-branch CI run; those suites were not redundantly rerun today. Historical local Terraform provenance below is retained from the foundation validation. No trained model, avatar or real AWS deployment has been tested.

| Check | Result | What it establishes |
|---|---|---|
| Python unit/in-process API tests | **54 passed** | JWT purpose/client/issuer/expiry/signature checks; local/cloud safety; bounded inputs; timestamp rules; content-free errors; absent models; language/signer/version separation; cancellation/admission behavior |
| Workbench unit/UI tests | **26 passed** | metadata, export, recorder limits/errors/disposal, capability states and camera permission behavior |
| Workbench TypeScript/production build | **Passed** | type checking and compiled assets; not hosting |
| Chromium browser tests | **5 passed** | actual API connection, simulated-camera MediaRecorder/playback/export with Python ZIP validation, denied permission, offline API, narrow-screen overflow, and missing-setup guidance/focus without accidental recording |
| Launcher teardown | **Passed in browser suite** | graceful SIGTERM shutdown of web, API and worker, without orphaned listeners |
| Actual hardware camera / Deaf ASL evaluation | **Pending** | simulated-camera tests do not establish real device usability or ASL accuracy |
| Real loopback gateway → worker HTTP smoke | **Passed** | liveness 200; authenticated capabilities list ASL/NSL as disabled; readiness 503; unauthenticated API 401; temporary processes stopped |
| Generated OpenAPI drift check | **Passed** | checked-in HTTP schema matches executable gateway |
| Terraform recursive formatting | **Passed** | canonical HCL formatting |
| Bootstrap Terraform validate | **Passed** | provider schema/configuration validity, without an AWS plan/apply |
| Development Terraform validate | **Passed, no warnings** | all referenced module configurations valid against the installed provider |
| Terraform mocked plan tests | **4 passed** | default excludes runtime/RDS/GPU; incomplete runtime/GPU configurations rejected; optional API/RDS/GPU full path plans with concrete mock inputs |
| JSON, Python syntax and Markdown local links | **Passed** | structured files parse and local documentation targets exist |
| Compose/workflow YAML parse | **Passed** | YAML structure parses; not a Docker or GitHub Actions execution |
| Terraform binary integrity | **Verified** | official Terraform 1.14.0 darwin_arm64 SHA256 matches downloaded archive |
| Provider installation and locks | **Verified** | AWS provider 6.73.0 installed with HashiCorp signature; generated registry lock/checksums retained in both roots |
| GitHub Actions references | **Pinned** | five official release tags resolved through GitHub's API to immutable commit SHAs |
| Git ignore safeguards | **Passed** | `.env`, virtualenv, `.terraform`, state and plan paths are ignored |
| Docker build / Compose runtime | **Passed in feature CI; not run locally in this review** | foundation image/Compose boot without a model |
| PostgreSQL migration / non-owner RLS | **Passed in feature CI; not run locally in this review** | real PostgreSQL 16 migration and non-owner isolation |
| Current feature GitHub Actions run | **Passed** | [4b2d33a](https://github.com/Neosignis/Infra-Setup/actions/runs/43724239789): application, workbench and Terraform jobs; draft PR remains unmerged |
| Real AWS plan/apply, credentials, quota, TLS/DNS and GPU runtime | **Not run** | account/region/budget/domain unconfirmed; no resources created |
| Real ASL recognition / signed response / avatar comprehension | **Not run** | no model, data, signer assets or reviewers supplied |

Commands used for the main checks:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/smoke_local.py
PYTHONPATH=src .venv/bin/python scripts/export_openapi.py --check
.venv/bin/python scripts/check_repository.py
terraform fmt -check -recursive infra
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev test
```

Terraform 1.14.0 was run from a temporary verified binary because it was not installed globally. Provider validation required permission for a local plugin socket outside the execution sandbox; mocked tests used no AWS APIs. The Python virtualenv reused matching preinstalled framework versions and installed JWT/cryptography/HTTP client dependencies locally. The successful feature CI run subsequently verified a Docker build and container boot; local Docker execution was not repeated here.

The feature CI run passed PostgreSQL, Docker and workbench steps on GitHub. They were not rerun locally during this documentation-only review. API tests use clearly isolated fixtures to validate engineering behavior; they do not measure sign-language accuracy or supply a demo provider.


Camera checks:

```sh
npm --prefix apps/workbench test
npm --prefix apps/workbench run build
cd apps/workbench
npm run test:e2e
```

Local browser validation used installed Chrome via `PLAYWRIGHT_CHROMIUM_EXECUTABLE`; CI installs Playwright Chromium. The browser archive was consumed by the Python integrity validator. Both the synthetic video and unit fixtures are engineering test inputs, not an ASL corpus. No recordings or provider weights are committed.


Architecture audit finding: a compact 300-frame full-feature synthetic payload is 4,331,796 bytes and exceeds the 4,194,304-byte body cap. This documents an unresolved transport limit, not successful full-length inference. See the [comparison report](reviews/2026-11-16-architecture-plan-review.md) for reproduction and scope.

## Dataset storage checks — 17 November 2026

Terraform 1.14.0 was downloaded from HashiCorp and checked against its published SHA256. The dataset root initialized with signed hashicorp/aws 6.73.0 using the committed lock. Terraform validate and recursive formatting checks passed. All six mocked storage runs passed: private/versioned/encrypted durable buckets, separate dataset/rights keys, approved-only read access for training, write-only intake, explicit no-email/no-alert behavior, gross-cost alerts before credits, and wrong-account rejection. The repository JSON/Python-syntax/Markdown-link check and git diff whitespace check passed. Mocks do not prove live AWS IAM enforcement, Free-plan service availability or deployment. No live account inventory, real plan or apply succeeded; local login remains pending. CI includes the new root, but these changes have not been pushed and no new remote CI run is claimed.

## Raw source acquisition — 18 November 2026

All 64 Python unit tests passed, including ten new read-only source-archive regressions covering download bounds/size, hash mismatch, unsafe paths, links, normalized duplicate paths, truncation, container-header reporting and preventing report output from overwriting an archive. The 925,061,120-byte PopSign hello validation archive completed downloading; inspection read and hashed 157 regular MP4 files, each with an ftyp header, with no rejected archive paths/links/duplicates. This is archive structure/integrity evidence, not video decoding, linguistic quality, signer-disjoint evaluation, data approval or model accuracy. Repository syntax/link/JSON and whitespace checks passed. One original clip was copied privately with a verified per-file hash. No data is committed, uploaded or used in training.

## ZIP acquisition support — 18 November 2026

All 71 Python tests passed after adding seven ZIP-specific integrity regressions (17 archive regressions in total). ZIP checks cover CRC corruption, unsafe paths, symlinks, normalized duplicate paths, expansion bounds, download size/hash limits and non-extracting behavior. No How2Sign ZIP was available for a real media integrity check: both requested validation video files returned Google Drive quota errors. Only the original English-reference text downloaded; 1,741 tab-separated records parsed with required fields and coherent numeric time ranges. This does not verify paired media, alignment, signing quality or training readiness. The temporary gdown 6.5.1 utility was installed outside project dependencies; the project virtual environment pip had a pre-existing Python/platform parsing issue, so the system Python was used only with a temporary --target directory. No global Python package installation was performed.

## Real How2Sign archive check — 18 November 2026

Read the user-provided frontal validation ZIP in place. Its 1,778,074,855 bytes hash to `6cb48170131fdb7fc64d40381a3c4be41112ba4454444170f5a31af2227b6d36`. All 1,739 MP4 members passed decompression/CRC, path safety and per-file hash reads; all have ftyp container headers. Exactly 1,739 IDs match the previously obtained original references, two reference rows have no media and no media lacks a reference. This verifies file identity/structure and ID correspondence, not decoded frames, language, actual timing alignment or model quality. The single preview copy was checked against its member hash.

## Real sampled decode and decoder tests — 18 November 2026

The bounded How2Sign probe reverified the source ZIP hash, then read/hashes matched source clips in memory and fully decoded 32 deterministic samples including shortest/longest original reference intervals. All 32 passed, with native 1280x720 frames, sample rates 24/30/50/60 fps, first-frame RGB24 conversion, and no sampled missing/non-increasing timestamps. The remaining 1,707 clips were not frame-decoded. No resize/crop/resampling/landmark extraction, ASL quality judgement or inference benchmark was performed. All 80 Python tests passed with the decoder present, including nine new video-probe tests using actual generated MP4 decoding, stable/extreme sampling, read bounds, invalid containers, changed source rejection and ZIP/reference integration. CI now installs the optional pinned decoder for these tests; no new remote CI result is claimed. The separate local data environment also ran the nine probe tests.
