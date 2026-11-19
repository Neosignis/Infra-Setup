# Local Interpreter experiment

Open `http://127.0.0.1:5173/#interpreter`. This screen accepts a complete recorded ASL message without asking for its meaning. **Contributor Studio**, at `/#studio`, is for collecting labelled evaluation clips. Studio labels are never sent to the Interpreter model.

## Try it

With the existing web/API/worker launcher already running, start the separate model service from the repository root:

```sh
python3 scripts/run_interpreter.py
```

For a fresh session with the dependencies and model assets installed:

```sh
.venv/bin/python scripts/run_local_demo.py --with-interpreter --open
```

Use one approach; do not start a second service on an occupied port. Dependencies and assets are described in [Mac ML setup](data/ml-dependencies-and-setup.md). `requirements-interpreter.txt` combines the application and ML dependency sets for a clean environment. No AWS deployment is required.

1. Enable the camera. Keep face, upper body and hands visible.
2. Select **Record a message**, sign, then **Finish message**.
3. Review the video and select **Interpret message**. Preview alone does not submit anything.
4. Expect either **Unverified suggestion** or **Please clarify**. Processing can take a minute or longer on this Mac.
5. Try Contributor Studio and return. The camera stops when changing screens; Studio retains its labels and clips in the tab.

The recording bound is 30 seconds / 16 MiB. Recordings reaching the deadline are rejected to avoid treating a cut-off message as complete. This experiment processes whole messages, not a live stream. It decodes WebM or video-only MP4 and keeps native frame timestamps. Mobile layout was tested in desktop Chrome with a narrow viewport; actual phone hardware remains untested. A phone cannot reach this Mac using the phone's own `127.0.0.1`; hosted HTTPS/mobile access is a later step.

## What is connected

```text
Browser recording → local job service → person + body/hand/face poses
                   → visibility/movement checks → Uni-Sign → output policy
                   → unverified suggestion OR clarification
```

The movement heuristic proposes an activity interval; it does not prove that movement is ASL or identify linguistic sentence boundaries. Translation still uses the complete message. No calibrated semantic confidence exists. The service therefore never labels a result verified and never supplies a percentage confidence score.

The draft everyday output scope includes greetings, thanks, yes/no, help, understanding, repetition, slower signing and wellbeing. It is enforced by a small English output allowlist, **not a validated ASL vocabulary detector**. Out-of-scope predictions are withheld. The model may still produce a wrong in-scope suggestion; the scope gate does not establish accuracy.

Typed replies are currently displayed as text. **Text-to-sign, reviewed signing clips, realistic avatars and real-time interpretation are unfinished.** The first offline translation differed from its reference; [baseline evidence](data/local-baseline-results-2026-11-18.md) is retained. No training has run.

## Local boundaries

- Video is processed in memory on this computer and is not saved by the service. Python/OS memory reclamation is not secure erasure. No clip is used for training.
- The service listens on loopback port 8002, behind the Vite development proxy `/research`. It is a local experiment, not an internet-facing deployment.
- One inference operation runs at a time. Cancelling clears its result; the operation retains admission until its thread exits. Short-lived text/job metadata remains in memory, with at most twelve jobs and ten-minute access expiry.
- The original `/v1` API, 553-point landmark contract, ten-second limits and provider approval state are unchanged. The experiment uses an independent video endpoint and 133-point pose schema.
- No AWS resources or new GitHub run were started for this work.

## Review checkpoints

| Check | Current evidence / next gate |
|---|---|
| No answer supplied with input | Raw-video transport, unit and browser tests |
| Video + pose processing | Actual held-out clip and real WebM decode checks |
| Uncertainty handling | Framing/movement/scope abstention and unverified-output tests |
| ASL → English correctness | Not passed; requires reviewed held-out messages and error analysis |
| Real-time speed | Not passed; profile complete pipeline and replace buffered design |
| Text → ASL | Pending complete reviewed utterance assets and playback |
| Release | Both translation directions, actual phone tests and Deaf ASL evaluation remain required |

Next model work: assemble permitted **training** data, keep validation/test data separate by signer and source, verify pose/text alignment, then fine-tune and compare on a frozen evaluation set. The current How2Sign validation download must not become training data. Unit tests establish software behaviour; they cannot establish ASL comprehension.
