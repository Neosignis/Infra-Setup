# API and streaming design

The executable contract is `openapi.json`, generated from the API. Implemented endpoints: process health, engine readiness, authenticated capabilities, short-utterance Recognize and Render. No session, streaming, speech, media download, escalation or lexicon endpoint is claimed implemented.

## Five target surfaces

| Surface | Proposed interface | Ownership and behavior |
|---|---|---|
| Recognize | `POST /v1/recognize` now; future stream frames | bounded ASL utterance to final text or abstention; unavailable is 503 |
| Render | `POST /v1/render` now; future async render jobs | typed text to approved asset ID or unsupported; no arbitrary output URLs |
| Converse | future `POST /v1/sessions`, `WS /v1/sessions/{id}/events` | session owner, language, output mode, signer, model pinning, stream epoch |
| Escalate | future `POST /v1/sessions/{id}/escalations` | user request → queued → partner accepted → connected → ended/failed; audit each transition |
| Lexicon | future `/v1/lexicon/proposals` and review transitions | submission → language expert review → approval/rejection → language-pack release |

API credentials identify the caller. For future tenant/session resources, authorize tenant membership and object ownership on every operation; a UUID is not authorization. Reviewer and data-steward roles are scoped per tenant/language. Contributors may inspect and withdraw their own grants; users cannot publish lexicon/model/identity assets directly.

## HTTP limits and semantics

The shipped foundation enforces a 4 MiB actual body limit, 2-300 frames, a maximum 10-second utterance, strictly increasing relative timestamps beginning at zero, exact landmark group lengths and finite bounded numbers. Missing groups are null. UTF-8 text is limited to 2,000 characters on render input. No video upload or URL fetch is exposed. `nsi` is reserved for NSL and is unavailable by default; `ase` denotes ASL.

Errors: 401 invalid/missing authentication, 413 oversized body, 422 invalid versioned input, 429 worker admission limit, 502 invalid engine output, 503 capability/provider unavailable, 504 upstream deadline. There are no automatic retries of a timed-out inference request. Worker errors do not echo request content. A non-null linguistic confidence requires an explicit calibrated flag; this contract cannot establish calibration evidence on its own.

Render returns an opaque asset ID. Authorized media delivery with consent/version checks, short-lived signed URLs, range requests and revocation is future work. A successful Render result alone does not make a playable avatar available in this foundation.

## Future stream envelope

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "session_id": "uuid",
  "stream_epoch": "uuid",
  "sequence": 42,
  "type": "recognition.final",
  "capture_time_ms": 1430,
  "language": "ase",
  "model_version": "approved-immutable-version",
  "payload": {}
}
```

Types: `session.ready`, `capture.quality`, `frames.accepted`, `frames.dropped`, `recognition.partial`, `recognition.final`, `recognition.abstained`, `render.started`, `render.segment`, `render.completed`, `escalation.state`, `error`, `session.closed`. Partial and final results share a segment ID and increasing revision. Final supersedes partial; clients do not speak partial text automatically. Non-manual/spatial plan payloads are separately versioned.

Proposed limits to validate: one active stream per development user, ten frames per feature message, a maximum 500 ms transient queue, 15-second heartbeat, disconnect after 45 seconds of silence, 10-minute idle session expiry. Numbers are design hypotheses, not shipped enforcement. Send negotiated limits in `session.ready`. Acknowledge processed sequence high watermarks; reject duplicates and out-of-order events, and reject old epochs after reconnect. Request resending an utterance when context is lost. Bound queues by bytes and age and test slow consumers.

Browser WebSocket authentication should exchange the access token for a one-use, session-bound, short-lived connection ticket over HTTPS. Do not put long-lived bearer tokens into a query string or log them. Validate origin, ticket, tenant, owner and expiry before upgrade. WebRTC signaling uses the same authorized session; TURN credentials expire and media consent is purpose-specific.

## Future sign plan

A sign plan needs language/dialect, semantic intent, manual articulations, spatial loci/referents, non-manual markers, timing, provenance and planner version. A renderer cannot safely infer these from English word order. Domain vocabulary changes enter a review workflow; lexicon approval does not automatically approve a model or full sentence realization.
