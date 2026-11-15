# First local camera release

This release makes the browser capture/evaluation path usable without AWS, Docker, signup or a trained model. It is not a foundation model or a working interpreter. ASL is first; NSL remains a separate language pack and release gate. Zoom and signup follow engine validation.

## Install and start

Requirements: Python **3.12**, Node.js **24** with npm, a camera and a recent Chrome or Edge browser. Terminal commands below are for macOS/Linux. Download Python/Node from their official sites or your existing version manager; `python3 --version` must show 3.12 and `node --version` must show 24 before creating the environment.

From the cloned repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix apps/workbench ci
.venv/bin/python scripts/run_local_demo.py
```

Open `http://127.0.0.1:5173`. Leave the terminal open; Ctrl+C stops the services. Add `--open` to ask the launcher to open your default browser. The launcher uses loopback ports 5173 (web), 8000 (API) and 8001 (worker), with a fresh in-memory development token. It ignores any ambient engine provider configuration. No AWS credentials or `.env` edits are required.

If these ports are occupied, stop your previous run or select three different ports:

```sh
.venv/bin/python scripts/run_local_demo.py --web-port 5174 --api-port 8020 --worker-port 8021
```

Use the printed URL. Camera access needs localhost/loopback or HTTPS; opening the HTML file directly is unsupported. `npm run build` compiles the client but does not provision hosting or a production API proxy.

## Review this build

1. Open the app. **Local API: Connected** and **ASL recognition: Not installed** should appear. Worker readiness 503 is expected while no model is installed.
2. Enable the camera and allow browser/operating-system permission. The preview should move; face, upper body and both hands should fit. No microphone is requested. Framing is a visual guide, not an automated check.
3. **Start recording** is directly below the preview. If setup is incomplete, selecting it explains the missing item and focuses that field; it does not begin recording. Enter a pseudonymous signer code and a reference to the separate recording permission record. A self-test may use `self-001` / `self-test-001` after your own explicit agreement. Do not type names or contact information. A checkbox is not a license, model approval or training permission.
4. Choose a proposed meaning, start recording, sign naturally and finish. Automatic stop is just before ten seconds; delayed/background-tab recordings longer than the limit are rejected. These English labels are meanings for ASL review, not signing instructions. If you are not fluent, test camera mechanics only and do not treat your recording as ASL ground truth.
5. Finishing a recording automatically opens **Session clips** with a saved confirmation. Play the recording, and check it actually contains the complete intended signing. Discard unwanted clips. Select **Unsupported meaning / no signing** for negative examples rather than forcing a supported label.
6. Download the session ZIP. Confirm it contains `manifest.json`, `README.txt` and `clips/`. Keep it in private storage outside GitHub. Closing/refreshing the page clears browser memory; downloaded files remain on disk.
7. Turn the camera off and confirm the browser/OS camera indicator switches off. Test a declined permission request too. Inspect the interface on your actual screen and report unreadable or clipped controls.

Return pass/fail for each item, your OS/browser, and any exact error text. Do not paste private recordings or permission documents into public issues. Real camera/device checks require your hardware; simulated-camera browser tests do not replace them.

## Export integrity

```sh
.venv/bin/python scripts/data/validate_capture.py /absolute/path/to/neosignis-local-session.zip
```

A passing result reports `capture_integrity_passed` and **`training_ready: false`**. It checks schema/language, recording permission metadata, label range, duration/size bounds, safe paths, duplicate IDs/hashes and video byte checksums. It does not decode the video, judge signing, verify a legal agreement or assign dataset splits. Training, distribution, motion and likeness permissions require separate evidence and review.

Each export has pending label/reference/rights review and unassigned splits. Assign train/validation/test by signer in a later reviewed ingestion step; session clips alone are not a representative dataset. NSL requires its own recordings and reviewers.

## Automated checks

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python scripts/export_openapi.py --check
.venv/bin/python scripts/check_repository.py
npm --prefix apps/workbench test
npm --prefix apps/workbench run build
cd apps/workbench
npx playwright install chromium
npm run test:e2e
```

CI runs a separate workbench job alongside the existing application and Terraform jobs. Browser tests use the real local HTTP services and a simulated camera, including a real recording, playback, export and Python integrity validation. Unit tests cover recording bounds/errors/cleanup, metadata validation, export contents, unavailable capabilities and UI permission handling. No inference benchmark can pass until real inference exists.

## What we need for sign-to-text

- A bounded meaning set confirmed by fluent Deaf ASL reviewers. The twelve labels in this build are proposed: hello, thank you, please, yes, no, help, understand, do not understand, repeat, sign more slowly, how are you, and I am fine. Include negative/unsupported input and important confusing pairs.
- A model/data route with verified code, weight and dataset permissions, runtime requirements, exact input schema, version/digest and supported scope. No weights or external recordings are included or downloaded by this release.
- Consented, reviewed recordings across multiple signers; signer-disjoint evaluation; a fixed holdout and reference labels. One developer's self-recordings are not a quality benchmark.
- A provider adapter and deterministic preprocessing checks, then real inference regression tests. Evaluate semantic correctness, coverage/abstention, false acceptance, signers/conditions, latency percentiles and cost. Agree numerical release thresholds before judging a model; they are not measured results today.
- After recognition passes, obtain reviewed response clips with appropriate playback rights and add response selection. Realistic avatars remain a separate linguistic/motion/comprehension milestone.

You can test this capture build now. The next decisions from you are who can provide fluent ASL review and whether we pursue licensed pretrained weights/provider access or an owned-data training route. AWS is needed only when we choose remote compute/hosting; its account, region, budget, IAM/OIDC, model deployment and real Terraform plan/apply are separate pending work.
