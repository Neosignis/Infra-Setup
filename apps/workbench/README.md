# Local camera workbench

Implemented React/TypeScript camera capture and review client. Start from the repository root using the [local demo guide](../../docs/local-demo.md). A trained sign-language model is not bundled.

## What works

- Explicit camera permission; video-only, mirrored preview and an unmirrored recording.
- Pseudonymous signer code and recording permission reference required before recording.
- Twelve proposed everyday meaning labels plus unsupported/no-signing examples; ASL review is pending.
- Start/finish, automatic stop before ten seconds, playback, discard and private ZIP export.
- At most 12 clips, 8 MiB per clip and 64 MiB per session; recordings remain in browser memory until downloaded.
- SHA-256 hashes and `neosignis.capture.v1` manifest, pending rights/reference review and unassigned dataset splits.
- Separate local API connection and recognition capability states. No invented translation or confidence.

The framing guide is visual only. Track settings are metadata, not measured frame loss or quality scores. No landmark extraction, inference request, signed response player, avatar, signup or hosting is implemented here. The static production build is checked for compilation; the development proxy is not a production authentication or hosting solution.

## Develop and test

Node.js 24 and Python 3.12 are required. Run `npm ci` in this directory, then:

```sh
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser tests start the real local API/worker and a separate Vite server on ports 5175/8010/8011. They use a simulated camera, exercise real MediaRecorder and playback, and validate the exported ZIP with the Python validator. No ASL accuracy is measured. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed Chrome binary when using that instead of Playwright's bundled Chromium. `npm run dev` alone is UI-only; engine status remains offline unless the API is started with the matching server-side development token.

## Next integration

Connect the selected provider's exact preprocessing/extractor contract to bounded recognition. Keep UI state separate from frame buffers and move extraction to a Web Worker. Measure actual frame rate and dropped frames; validate orientation against golden recordings. Never equate gesture labels with ASL translation. Add model scope, abstention and correction only once a real model produces them. See [engine design](../../docs/engine.md).

Cloud authentication, media storage and human escalation need their own implemented services and acceptance evidence before being presented as available. Use Cognito authorization code + PKCE for a later cloud client; do not place development tokens or AWS keys in a browser build.
