# Implementation and validation status

Status date: 15 November 2026. This is an architecture and engineering foundation, not a completed sign-language interpreter or production deployment.

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

## Validation record

The final validation results are in [validation.md](validation.md). Local checks do not establish AWS deployment success, Docker compatibility, PostgreSQL runtime behavior or linguistic quality unless those specific checks were run.

## Not implemented or not supplied

No trained/approved model, ASL dataset, real inference provider, camera-to-model feature extraction, speech integration, live stream/session orchestrator, sign planner, recorded signer footage, avatar rig/identity, neural renderer, authorized media-delivery endpoint, human dispatch partner, lexicon workflow, withdrawal processor, royalty settlement or meeting-platform integration is supplied. The schema and provider seam are starting points; they are not implementations of those workflows.

Model capability flags are provider assertions in the foundation. Production approval must come from server-controlled registry evidence/digest checks, not a provider boolean. Tenant resource authorization, database access roles/secret rotation and app/database wiring are not complete. Shared production service auth, WAF/rate policy, complete telemetry, alarm routing, dependency locks/base image digests and recovery evidence remain release gates.

Only the dev Terraform root exists. Staging/production accounts and roots, static web hosting, media transport/TURN, background SQS jobs and DNS/ACM issuance are designed but not provisioned by this foundation. Optional GPU resources do not install models or CUDA dependencies into the foundation image. Review each actual model's runtime/image separately.

## External setup pending

The source is now in [Neosignis/Infra-Setup](https://github.com/Neosignis/Infra-Setup). Foundation checks succeeded on the existing main commit `3dd716e5b864dbef001e57f38e48c0b242122e7f`; see the [run](https://github.com/Neosignis/Infra-Setup/actions/runs/43471557522). The local camera changes are prepared on `codex/local-camera-workbench`; a new CI result is separate evidence from the earlier foundation run. No AWS inventory, real plan/apply or deployment was performed. AWS account/region/budget/domain are unconfirmed. Supplied confidential reference documents and private recordings are not copied into the repository.

## Next engine milestone

Obtain a rights-cleared ASL model/data path and paid Deaf ASL review. Freeze a bounded phrase set and signer-independent holdout. Use the camera workbench to collect reviewed evaluation samples, implement exact preprocessing and the real provider, run G1, then add reviewed signed responses for G2. A realistic-avatar claim waits for G3. Platform adapters follow those engine gates.

Run and review the capture milestone with the [local demo guide](local-demo.md). Camera/export success is separate from G1 linguistic recognition quality.
