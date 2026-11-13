# Operations and recovery

The foundation has health checks, explicit unavailable errors, CloudWatch log groups, ECS container insights, an ALB unhealthy-host alarm without an action destination, and an optional account-wide cost alert. Full telemetry and incident routing are not implemented.

## Health and readiness

`/healthz` is process liveness; use it for ALB/container restarts. `/readyz` reflects whether an approved provider is available and returns 503 by default. Do not use model readiness as a restart trigger that loops an otherwise healthy API. A shared engine must report capability readiness per language and direction rather than a single global green light.

If text is not produced: check authenticated capabilities, input schema/version, model/provider installation, worker admission, frame capture quality, worker logs without content and pinned artifact approval. Never resolve unavailable errors by enabling a fake provider. A model load failure should fail worker startup or disable that capability with an operational alert.

## Metrics to implement with the first model

Request count by endpoint/status, active streams, rejected/abstained utterances, GPU utilization/memory, model load/cold-start, frame drop/age, queue depth/wait, preprocessing/inference/planning/render latency, end-to-end P50/P95, comprehension/task success, and cost per successful minute. Do not use signer ID, user ID or phrase text as metric dimensions. Traces carry opaque correlation IDs, never content/tokens/landmarks.

Starting alarm hypotheses: sustained readiness failure for an enabled language; any rights-revocation processing failure; 5xx rate above an agreed baseline; queue age above the negotiated stream limit; high GPU memory; unhealthy API hosts; unusual storage/egress; budget threshold. Assign owner, notification route and runbook before shared use. A CloudWatch alarm without a notification target is not on-call coverage.

## Recovery objectives and exercises

Proposed metadata RPO 24 hours/RTO 4 hours for development; production objectives need agreement and load/restore evidence. RDS seven-day automated backups support point-in-time recovery when enabled; no successful restore has been performed. S3 versioning aids accidental overwrite recovery but does not ensure contributor withdrawal.

Exercise: restore RDS to a new private instance; apply schema version checks; reapply post-backup deletion/withdrawal ledger; validate non-owner RLS; point a staging API at the restored endpoint using a rotated restricted credential; run content-free integrity checks and consented smoke test; record actual recovery time and loss. Never overwrite a live database as the first recovery action.

State recovery: confirm no other Terraform operation is active, inspect state object versions and lock ownership, restore the reviewed state version to an isolated validation context, compare with real resources, then reconcile under platform lead supervision. Never force-unlock without proving the owner is dead. Do not publish plan/state artifacts in a public CI job.

## Incidents

Wrong/unsafe interpretation: stop affected model/language capability, preserve minimal incident metadata with consent, provide text/correction and real human route, classify the error with Deaf reviewers and require a new release gate. Rights withdrawal: freeze affected signer/model and execute the lineage workflow. Suspected access compromise: restrict ingress, revoke roles/tokens, rotate affected secrets, investigate least-privilege audit records, then restore from a verified version.

Capacity failure: reject excess work visibly, stop new sessions, avoid retry storms, keep existing workers bounded, and change pool limits only after cost and quota review. Timed-out provider work may continue until the provider finishes; hard inference deadlines/cancellation need a supervised process or serving runtime before live streaming.

## Configuration reference

| Variable | Purpose | Default / rule |
|---|---|---|
| `APP_ENV` | deployment safety boundary | `local`; cloud cannot use dev token |
| `AUTH_MODE` | bearer verification | `dev_token` locally; `cognito` in AWS |
| `DEV_API_TOKEN` | local-only secret | required random 32+ characters, never committed |
| `COGNITO_ISSUER` | JWKS/issuer trust | fixed regional HTTPS user-pool URL |
| `COGNITO_CLIENT_ID` | allowed app client | required in Cognito mode |
| `INFERENCE_URL` | trusted worker origin | local loopback or private Cloud Map DNS |
| `ENGINE_PROVIDER` | reviewed import factory in worker image | unset means all capabilities unavailable |

Model storage locations, digests and provider-specific settings must be documented by each actual provider. Never accept arbitrary paths/URLs from clients or persist runtime secrets in Terraform state unnecessarily.
