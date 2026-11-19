# MVP acceptance baseline

Confirmed by the founder on **18 November 2026**: **phone and web, ASL, in-person use, real-time text-to-sign and sign-to-text**. Phone delivery is through **mobile browsers**, alongside desktop browsers. Both directions are required in one release. This is the acceptance baseline, not a claim of implemented functionality.

## The successful conversation

Two people are together in person. The Deaf participant signs into the phone or computer camera. The application interprets the supported utterance and displays its English meaning. The other participant types a reply, submits it, and receives understandable ASL signing. They can repeat this exchange in the same session.

Publish the supported everyday-conversation scope and have fluent Deaf ASL reviewers approve it before evaluation. Include complete utterances, not only letters or isolated signs. The hearing participant supplies the response; generating chatbot replies is a separate feature.

## Required review checklist

| Check | Pass evidence |
|---|---|
| Mobile and desktop browsers | Complete conversation passes on actual supported phones and desktop browsers |
| Live sign-to-text | New camera signing produces meaning-preserving English text from actual inference |
| Text-to-sign | Submitted text produces complete, reviewed ASL output for supported meanings |
| In-person session | Repeated turns work without exporting or uploading recordings for each utterance |
| Interactive response | Both directions pass agreed latency thresholds on declared devices and networks |
| Language quality | Independent ASL review and signer-disjoint evaluation pass thresholds frozen before final testing |
| Unsupported input | Unclear signing or unsupported text prompts clarification rather than invented text or unrelated signing |
| Phone-readable signing | Hands, face and relevant body motion remain visible; output can be replayed, paused and stopped |
| Session reliability | Permission denial, interruption, connection loss, cancellation and stale results recover predictably |
| Rights and privacy | Explicit camera permission, no default retention for training, and approved model/output assets |

## What real-time means

The camera path processes signing during the live session and handles utterance completion. Some temporal buffering is necessary. An active preview or manual clip-export workflow alone does not satisfy the interaction.

Record P50 and P95 for both directions on each supported device/network:

- **Sign-to-text:** end of signing to the correct final English text on screen, including capture, transport, inference and display.
- **Text-to-sign:** submit action to the start of meaningful signing, including planning, rendering/retrieval, transport and playback startup. Check that the entire output completes correctly too.

Initial engineering proposal: **P95 within two seconds in each direction for the declared short-utterance scope and tested conditions**. This is a proposed target, not a founder-approved threshold or measured result. Do not accelerate signing to meet it. Quality, sample counts, coverage and false-acceptance thresholds still need agreement before final evaluation; values remain null in the [acceptance template](../ml/evaluation/acceptance.example.json).

## Signing output and scope

The existing decision remains: consented, reviewed recordings of complete ASL utterances can establish the first response milestone, followed by a validated realistic-avatar backend. Submitted text must drive the appropriate output within the declared scope. A limited clip library must not be described as unrestricted translation; stitching isolated word clips does not establish grammatical ASL.

Realistic-avatar claims require separate likeness/motion rights and comprehension evidence. Speech, NSL, meeting-platform adapters and native installed phone applications remain later scope.

## Build and data implications

1. Establish the ASL model/data/rights path and reviewed full utterances, including confusing and unsupported examples. Preserve independent held-out signers.
2. Build the live camera/extractor/temporal inference/text path. Public isolated-sign datasets support diagnostics; they cannot alone establish conversational interpretation.
3. Build text handling, reviewed response assets/planning, authorized media delivery and phone-readable playback.
4. Join both directions in a responsive session with turn handling, cancellation, uncertainty and bounded processing.
5. Provide a reachable test deployment and verify the full exchange on actual phones and desktop hardware. Desktop localhost success alone does not pass the device gate.
6. Run unit, integration and browser tests alongside separate linguistic evaluation. Software tests check mechanics; real-signing holdouts and Deaf comprehension review check language quality.

Current implementation is a capture/review/export workbench plus API/provider and infrastructure foundations. No trained recognition, working signed output or live interpretation session is installed. The MVP is not complete. See [implementation status](status.md) and [dataset access](data/dataset-access-and-mvp-guide.md).
