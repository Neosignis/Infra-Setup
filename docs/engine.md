# First engine and model strategy

The [confirmed MVP](mvp-acceptance.md) requires live in-person ASL sign-to-text and text-to-sign together in mobile and desktop browsers. Recognition and reviewed-response milestones below are intermediate engine steps; neither alone completes the MVP.

The first success is a real ASL signer producing correctly interpreted text on unseen signing examples. A second milestone plays a reviewed response in ASL. A realistic signing avatar is a later output backend whose visual quality cannot substitute for linguistic correctness.

## Week one scope

Select a bounded phrase/intent set with paid fluent Deaf ASL reviewers. Record negative/out-of-scope examples as well as accepted phrases. Keep complete sentences where possible, including questions and negation. Label the experiment as bounded phrase recognition. Require separate signers in development and final holdout; splits from the same recording or same person do not establish signer independence.

Candidate baseline tracks are (1) a licensed pretrained temporal recognizer suitable for our input, and (2) a small temporal model trained on consented domain data. Model selection is deliberately not invented: no checkpoint, rights record or measurements were supplied. Compare language/domain coverage, commercial use rights for code/weights/training data, inference hardware, preprocessing, accuracy, abstention and latency before approval. A generic gesture recognizer is not an ASL translator.

If data/model access is missing this week, complete capture, contracts and deployment checks, then report an infrastructure-only milestone. Do not present a scripted text return as recognition.

## Recognition pipeline

Capture both hands, face and upper body with monotonic timestamps and missing landmarks. Compare RGB, landmarks and hybrid approaches on the same held-out signers and conditions. Include handedness, occlusion, camera mirroring, orientation, frame rate and coordinate convention in preprocessing. The shipped foundation accepts `neosignis.landmarks.v1`: 33 pose points, 21 left-hand points, 21 right-hand points, and 478 face points; a missing group is null. These are normalized image-space coordinates, with per-point visibility optional. Extractor and model must agree exactly. Do not treat extractor tracking scores as linguistic confidence.

Temporal modelling must account for motion, coarticulation, segmentation, spatial references and non-manual signals. Continuous recognition and translation are separate later evaluation tracks from bounded phrase classification. Fingerspelling, names, numbers, negation and question structure need dedicated coverage. A semantic representation carries alternatives, source spans, uncertainty and context; gloss may be an auxiliary annotation, not the only interchange format.

The worker provider interface is in `src/neosignis/providers.py`. A deployment installs a provider via `ENGINE_PROVIDER=package.module:factory`. The factory returns a provider whose capabilities declare approved languages and model versions. There is no default recognizer or renderer. A provider is trusted code installed through a reviewed image build; the API never accepts a user-supplied import path or model URL.

## Artifact promotion

An immutable model manifest must include model ID/version, SHA256, input schema, preprocessing version, language/dialect, bounded domain, training and evaluation lineage, code/weights/data rights, measured hardware, memory/latency profile, calibration status, known failure modes, approval identities and withdrawal links. The sample schema is in `ml/model-manifest.schema.json`.

Promotion is research → candidate → Deaf-reviewed validation → approved for bounded internal demo → pilot → production. Each promotion has immutable evidence and a rollback version. Independent models/calibration are released per language; ASL approval does not activate NSL. A provider's self-reported `approved` boolean is only a foundation contract; production must enforce a server-controlled signed/authorized registry record and artifact digest before loading it.

## Response generation and rendering

The initial response comes from the hearing participant's typed text. Exact approved phrase mappings can select a complete consented ASL clip. They must reject unsupported paraphrases until reviewed. Clip metadata identifies signing language, meaning/intent, contributor, license/consent version, asset digest and approved context. Human signing footage is labelled as recorded output.

For a motion-driven avatar, create or license a rig with sufficient finger articulation, wrist/arm/torso motion and facial controls. Retarget reviewed motion and preserve contact, hand shape, location, movement, eye gaze and facial grammar. Evaluate from the camera angle used in the product; a rig can look plausible while conveying the wrong sign. A human-realistic surface can be applied only after this motion path is comprehensible.

For neural human rendering, use a consented identity model and motion-conditioning capable of preserving hands, face and timing. Require per-contributor training/rendering/derivative licenses and withdrawal procedures. Generic image or talking-head generation does not establish sign fidelity. Signer style, dialect and identity must be independently evaluated; clothing/skin/age customization must not change the linguistic motion silently.

The target signer library of three to five contributors is a product goal from the supplied references, not an asset currently available. Royalty accounting records delivered render usage with idempotent event IDs and consent version. No biometric or likeness data goes into Git history.

## Speech

ASR and TTS are replaceable providers. Partial ASR can be corrected, so only stable reviewed segments should drive committed signing. Speech-to-sign latency includes ASR, semantic planning, sign generation and first valid rendered frame. Names/numbers and multi-speaker attribution need explicit evaluation; multi-speaker diarization is outside the first demo.

## Evaluation and acceptance

| Gate | Evidence required | Release consequence |
|---|---|---|
| G0 rights and scope | authorized data/model/identity, reviewer agreement, supported phrase set | no training/promotion without it |
| G1 recognition | signer-independent holdout, per-class and semantic errors, negatives, abstention and latency | bounded recognition demo only |
| G2 response comprehension | Deaf reviewers recover intended meaning from output, including non-manual grammar | response loop demo |
| G3 realistic avatar | rig/identity rights, hands/face fidelity, comprehension compared with recorded signer | realistic avatar option |
| G4 controlled pilot | accessibility, uncertainty, privacy/deletion, operational recovery, human route | limited consenting pilot |
| G5 channel adapter | measured engine quality plus transport/platform review | integration release |

Before seeing held-out results, reviewers and ML lead agree numeric thresholds in `ml/evaluation/acceptance.example.json`. The example leaves them null intentionally so unagreed thresholds cannot look like passed gates. A release report must include sample counts, signer counts, split policy, model digest, conditions, P50/P95 latency, semantic error categories, coverage, abstention and review method. Automated text metrics supplement, not replace, comprehension tests.

Cost per successful interpreted minute = attributable GPU + CPU + storage/egress + speech provider cost divided by successfully interpreted minutes. Also report occupancy and idle cost separately; a warm GPU with no sessions still costs money. Contributor compensation and human interpretation costs are separate commercial inputs.

## Dataset caution

The How2Sign maintainers publish the dataset under CC BY-NC 4.0 and explicitly prohibit commercial use. It cannot be assumed to be commercially cleared training data. [How2Sign maintainer source](https://github.com/how2sign/how2sign.github.io/blob/main/index.html). Review each other dataset and checkpoint on its own terms, including upstream video and identity rights. No legal clearance is inferred by this repository.
