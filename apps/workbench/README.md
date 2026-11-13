# Camera workbench implementation contract

The workbench is the first engine client. Its design is specified here; a finished browser application is not included in this architecture foundation.

Use React with TypeScript, with capture/tracking in a Web Worker and UI state separated from frame buffers. Screens: local setup/camera permission, framing preview, live interpretation, response text/signer playback, and correction/evaluation. Display the active language, model scope and capability status. Disable interpretation when the engine reports unavailable; do not animate a fabricated translation.

Capture must include upper body, both hands and face. Mirror the preview for usability while preserving an explicit camera-to-model orientation transform. Measure actual frame rate and mark dropped frames. Never equate a MediaPipe gesture label with an ASL translation. Use the worker's exact feature/preprocessing schema; test browser/extractor versions against a golden recording before release.

Authenticate through Cognito authorization-code + PKCE for cloud. Keep tokens in memory or a reviewed secure-session pattern, never persistent browser storage by default. Local foundation uses a developer token entered by the developer; never bake it into the web build. Public browser assets may eventually be hosted on S3/CloudFront with private origin access; hosting is outside the shipped Terraform modules.

Start with bounded utterance HTTP requests to `/v1/recognize`; add streaming only after the input path is measured. Responses show nullable confidence, abstention and explicit correction. Typed responses go to `/v1/render`; player output labels recorded signer versus avatar. Every unsigned/unsupported response retains readable text.

Keyboard access, visible focus, screen-reader labels, color-independent uncertainty states, large text, no autoplay audio, consent controls, reduced motion and a stable signing viewport are acceptance requirements. Test with Deaf users and actual phones/tablets, including low light, busy backgrounds, weak links and camera occlusion.

The application must not store capture in localStorage, analytics or error reports. Opt-in evaluation capture requires a separate purpose/retention dialog and authorized storage path. Human escalation is shown as available only after a real partner connection exists.
