# Implementation and validation status

## Latest: exact training source videos and review packet, 19 November 2026

Downloaded [all eight matching RGB clips and prepared the review packet](data/source-video-review.md). All 750 source frames match the stored pose counts/indices. Side-by-side source/pose videos preserve decoded frame timestamps. Forty sampled comparisons against our current extractor triggered no large spatial-disagreement flag; this is an uncalibrated consistency diagnostic, not language or pose ground truth.

The offline review page, CSV worksheet, contact sheet and portable ZIP are ready under ignored local review storage. **178 local Python tests passed**, including nine new diagnostic/media/packet tests; browser checks verified playback, reference reveal, notes export and mobile layout. The questionable caption remains flagged, all linguistic review remains pending, and no labels or model weights were changed. No cloud resources were started.

## Latest: first small local adapter trained, 18 November 2026

Completed [32 optimizer updates on eight ASL training utterances](data/first-local-training.md), fitting a 25,360-parameter residual adapter over the frozen 587,747,368-parameter baseline. Two development validation examples were excluded from fitting. CPU experiment time: 45.79 seconds. Saved a separate 104,157-byte adapter; the original baseline is still required.

Training loss fell from 0.7493 to 0.6349. Validation loss rose from 3.8070 to 3.8395, and both generated validation predictions stayed unchanged and differed from their references. This verifies training mechanics, not improved translation. The adapter was not promoted to the browser or approved API provider. Separate checkpoint restoration/evaluation reproduced the final validation loss. **169 local Python tests passed**; no cloud resources were started.

## Latest: real training-data process pilot prepared, 18 November 2026

Prepared [32 genuine How2Sign training pose utterances](data/training-preparation.md), retaining all 4,203 frames and full English targets from pinned publisher-maintainer annotations. Downloaded only selected byte ranges from the publisher's pose ZIP. The numeric training cache is 5.13 MB. No model fitting occurred.

Indexed all 1,739 local validation clips, recorded the two missing videos separately, and extracted two complete validation feature sequences with original timestamps. No validation clips were assigned to training. The 31,086 training annotation rows and local validation references have no source-video overlap; signer independence remains unverified. One nine-frame training clip is flagged for review. All linguistic/alignment review is pending.

The [numeric dataset loader and reproducible checker](data/training-preparation.md) passed hash, full-frame, full-target, split and PyTorch DataLoader checks. **159 local Python tests passed**, including 18 preparation tests and a verified-cache resume test. This is a small process pilot, not enough data or evidence for the everyday MVP. Data is Git-ignored local storage; no AWS resources or optimizer steps were started.

## Latest: separate Interpreter and Contributor Studio, 18 November 2026

The default browser screen is now the [Interpreter experiment](interpreter-experiment.md). It records whole messages with no meaning labels and submits raw video to an independent loopback service. Contributor Studio retains recording labels, permissions metadata and session ZIP export. Cameras stop when changing screens; Studio details remain in the tab.

Connected person/body/hand/face pose extraction, uncalibrated movement/visibility checks, the installed Uni-Sign baseline, asynchronous one-at-a-time jobs, progress, cancellation and output abstention. All exposed predictions are explicitly unverified and confidence remains null. This is buffered video processing, not live interpretation or an approved production provider. The original API contract/provider state is unchanged.

A real 82-frame held-out How2Sign clip passed through the HTTP job service and translation stage in **61.22 seconds** on CPU, then correctly triggered the outside-scope output policy: no candidate was exposed. This checks pipeline wiring and withholding, not translation correctness or recall. The preceding offline prediction for that clip was wrong. No training has run. Text-to-sign assets, Deaf ASL evaluation, actual phone hardware and real-time performance remain unfinished; the MVP is not complete.

Local verification: **141 Python tests**, **37 frontend tests**, **8 Chrome browser tests** passed, including simulated-camera recording, raw video submission without labels and narrow layouts. Browser model outcomes are controlled test fixtures; they do not establish ASL accuracy. Changes remain local; no AWS resources or new GitHub run were started.

## Latest: installed ML runtime and first real prediction, 18 November 2026

The [Mac dependency set](data/ml-dependencies-and-setup.md) is installed. Checkpoint identity/tensor validation and complete CPU model restoration passed. Detector, pose and tokenizer assets are local and ignored by Git. The [first real validation-video run](data/local-baseline-results-2026-11-18.md) produced text, but differed from its reference and did not pass semantic quality; its CPU timings do not meet live-MVP requirements. No ASL training has run.

The user confirmed permitted model use on 18 November; this session has no pending request to reconfirm that authorization. The factual asset/source records are retained separately. At this earlier checkpoint the runtime was offline; the subsequent browser experiment is described above. It remains separate from the approved API provider. Changes remain local and no AWS resources were started.

## Latest: pose adapter and local compute, 18 November 2026

Implemented an independent 133-point body/hand/face input adapter and tensor-checkpoint validator, with 16 additional tests. The full local suite passes **114 tests**. [Details and remaining integration work](data/pose-adapter-and-local-training.md).

Verified this ARM64 MacBook Air has 8 GB shared memory and can complete a tiny synthetic optimizer step on MPS with PyTorch 2.9.0. This is not an actual Uni-Sign capacity/performance test. Keep preparation and small tests on the Mac; plan substantial fine-tuning on cloud GPU after profiling and explicit spending approval. No cloud resources were started.

Pinned reviewed upstream source revision; no explicit Uni-Sign code licence found. Code permission, noncommercial weight/data limits, real pose extraction, model/runtime assets and permitted training data still need resolution. No Uni-Sign weights loaded, ASL training or model accuracy result exists.

## Latest: variable-length loader and model selection, 18 November 2026

Implemented the [offline loader](data/training-loader.md): complete ZIP clips, native timestamps, versioned feature extraction interface, missing-observation masks, padded batches/targets and length buckets with explicit resource bounds. Added 18 loader tests, including real MP4 and PyTorch DataLoader checks; the full local Python suite passed **98 tests**. OpenAPI remains unchanged. A separate CPU PyTorch CI job is configured locally, not yet run remotely.

Four real How2Sign clips fully decoded through the new loader. One has 1,704 frames and a ~70.96-second timestamp span despite a 53.22-second reference interval; alignment remains unverified. No poses, training or accuracy results were produced.

Selected [Uni-Sign How2Sign pose-only SLT](recognition-model-decision.md) as the first research baseline with a pinned publisher checkpoint revision/hash. This is not a verified production selection: weights are noncommercial, code terms/revision and runtime still need review, pose/checkpoint integration is pending, and nothing is downloaded or installed. The public ten-second API limit, browser capture behavior and AWS deployment status are unchanged.

The [confirmed MVP](mvp-acceptance.md) requires live in-person ASL sign-to-text and text-to-sign in mobile and desktop browsers. Both directions and actual phone/browser evaluation remain pending; capture, dataset access checks and infrastructure tests do not complete this release.

Status date: 18 November 2026. This is an architecture and engineering foundation, not a completed sign-language interpreter or production deployment.

Reviewed architecture and milestone baseline: [System Architecture and Delivery Plan v2.0](neosignis-system-architecture-and-delivery-plan.md). The [comparison report](reviews/2026-11-16-architecture-plan-review.md) flags unsupported claims and current implementation gaps.

## Delivered

- Requirements/source review and empty-workspace audit.
- System context, runtime and database diagrams; stack decisions and tradeoffs.
- ASL-first engine architecture and independent NSL language-pack design.
- Recognition, semantic planning, sign generation and realistic-renderer boundaries.
- Typed authenticated HTTP API and private provider host, with explicit unavailable defaults.
- Docker/Compose configuration and local Python execution path.
- React/TypeScript camera workbench: permission, bounded video-only capture, review/discard and private ZIP export with hashes and pending-review metadata.
- One-command local launcher, capture-integrity validator, frontend unit/browser tests and a dedicated workbench CI job.
- Terraform state bootstrap, VPC/security groups, private S3/KMS, ECR, Cognito, optional TLS API runtime, optional RDS and optional zero-task GPU pool.
- PostgreSQL rights, asset, dataset/model lineage, evaluation, session and usage schema with forced tenant RLS.
- OpenAPI and future Converse/Escalate/Lexicon/streaming specifications.
- GitHub CI/image-publish workflows, OIDC policy examples and team issue template.
- Delivery plan, security/data-governance, deployment, recovery and migration documentation.
- Competitor/data acquisition study, contributor brief, source register and a downloaded PopSign hello/validation archive: 157 MP4 files with size/structure/hash checks. No dataset is approved for training.

## Validation record

The final validation results are in [validation.md](validation.md). Local checks do not establish AWS deployment success, Docker compatibility, PostgreSQL runtime behavior or linguistic quality unless those specific checks were run.

## Not implemented or not supplied

No trained/approved model, approved ASL training dataset, real inference provider, camera-to-model feature extraction, speech integration, live stream/session orchestrator, sign planner, recorded signer footage, avatar rig/identity, neural renderer, authorized media-delivery endpoint, human dispatch partner, lexicon workflow, withdrawal processor, royalty settlement or meeting-platform integration is supplied. The schema and provider seam are starting points; they are not implementations of those workflows.

Model capability flags are provider assertions in the foundation. Production approval must come from server-controlled registry evidence/digest checks, not a provider boolean. Tenant resource authorization, database access roles/secret rotation and app/database wiring are not complete. Shared production service auth, WAF/rate policy, complete telemetry, alarm routing, dependency locks/base image digests and recovery evidence remain release gates.

A separate dataset-storage Terraform root is now prepared alongside dev; neither has been deployed here. Staging/production accounts and roots, static web hosting, media transport/TURN, background SQS jobs and DNS/ACM issuance are designed but not provisioned by this foundation. Optional GPU resources do not install models or CUDA dependencies into the foundation image. Review each actual model's runtime/image separately.

## External setup pending

The source is in [Neosignis/Infra-Setup](https://github.com/Neosignis/Infra-Setup). Main remains at `3dd716e5b864dbef001e57f38e48c0b242122e7f`. The camera workbench and recording-flow fix are on `codex/local-camera-workbench`, commit `4b2d33ab271cf3d9fca9b4248dd2dc25e2782b71`, in [unmerged draft PR #1](https://github.com/Neosignis/Infra-Setup/pull/1). Its [CI run](https://github.com/Neosignis/Infra-Setup/actions/runs/43724239789) passed application, workbench and Terraform jobs. Research/review document additions are local working-tree changes, not merged features. No AWS inventory or real plan/apply was performed or cloud deployment verified. The user has confirmed AWS account 324793866495, us-east-1 and a Free plan with a reported $100 credit. Local access remains unverified: the CLI is 2.31.18, old profiles belong to another account and their session is expired. Console/CloudShell login does not authenticate this Mac. The collection budget remains a draft $25 alert threshold; the email and domain are unset. Potential contributor introductions are available. Supplied confidential source documents and private recordings are not copied into Git history.

## Next engine milestone

Obtain a rights-cleared ASL model/data path and paid Deaf ASL review. Freeze a bounded phrase set and signer-independent holdout. Use the camera workbench to collect reviewed evaluation samples, implement exact preprocessing and the real provider, run G1, then add reviewed signed responses for G2. A realistic-avatar claim waits for G3. Platform adapters follow those engine gates.

Run and review the capture milestone with the [local demo guide](local-demo.md). Camera/export success is separate from G1 linguistic recognition quality.

## Newly documented blockers

A compact synthetic 300-frame/553-point request measures 4,331,796 bytes, exceeding the 4 MiB middleware limit; the chosen inference transport needs a real payload regression and model-specific design. The seven-day research lifecycle is unsuitable for permanent datasets, so durable dataset storage/intake is separate pending work. Existing ALB default forwarding does not block gateway docs/readiness paths; approval enforcement, shared service authentication, authorisation and observability remain pilot gates. These findings were documented, not silently fixed in runtime/infra code by the architecture review.

## Dataset storage preparation — 17 November

A separate storage-only root, scoped unattached IAM policies, optional gross-cost budget alerts and six passing mocked Terraform tests are prepared under `infra/environments/datasets`. Terraform validation and formatting passed locally. Follow [AWS collection setup](data/aws-collection-setup.md). No real dataset plan/apply, AWS inventory, upload service or training loader has run. The permanent buckets retain completed files/versions; the existing research bucket remains short-lived.

## First raw sample — 18 November

A 925,061,120-byte PopSign v1.0 game/val/hello archive was downloaded locally and contains 157 MP4 files. Size, structure, file hashes and video container headers were checked; video decoding and ASL review remain pending. Raw data/per-file inventories stay under ignored `data/local/`; an original clip copy is available for private playback. The [acquisition summary](data/popsign-sample-acquisition-2026-11-18.json), [draft meanings](../ml/data/everyday-meanings.draft.json) and [execution checklist](data/pilot-execution-checklist.md) record the boundaries. No fluent reviewer is available yet; online reference lookup is research, not independent linguistic approval. All 64 Python tests pass, including ten new archive tests. No S3 upload, approved corpus or training run has occurred.

## How2Sign access — 18 November

Downloaded only the original validation English-reference text: 311,131 bytes and 1,741 sentence records. Both official frontal and side-view validation ZIP links returned Google Drive quota-exceeded errors; no How2Sign video was acquired. The realigned-reference link was not retrievable anonymously. See [download status](data/how2sign-download-status.md). The archive inspector now supports ZIP CRC/hash/path checks; all 71 Python tests pass, including 17 archive regressions. No commercial permission, model training, signed-in Google-cookie access or AWS upload occurred.

## User-provided How2Sign archive verified — 18 November

The user supplied `/Users/user/Downloads/val_rgb_front_clips.zip` (1,778,074,855 bytes), resolving local access to the frontal validation footage despite the earlier automated Google Drive quota failure. CRC/path/hash/container-header checks passed for 1,739 MP4 files. Every video matches an original English-reference ID; two of 1,741 reference rows lack corresponding videos and remain flagged. No full extraction, archive duplication, video decoding, ASL review, AWS upload or model training occurred. A bounded private clip copy is available for playback. The raw ZIP remains in Downloads. See [acquisition evidence](data/how2sign-acquisition-2026-11-18.json).

## Sampled video decoding — 18 November

All 32 deterministically sampled How2Sign clips fully decoded with PyAV 19.0.2. Sampled clips are 1280x720, with reported rates of 24/30/50/60 fps and no sampled timestamp-order issues. This is 32 of 1,739 clips, not complete-corpus decoding or linguistic approval. Across matched original reference rows, 240 utterances exceed the existing ten-second API input cap; the longest reference interval is about 53.22 seconds. See [preprocessing readiness](data/preprocessing-readiness.md). The versioned model-input/session design remains pending; no training/preprocessing transforms, real recognition or signed-output feature was installed. A separate ignored `.venv-data` supports local reruns, and all 80 Python tests passed locally.
