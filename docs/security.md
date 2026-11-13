# Security privacy and data governance

The foundation protects a development API boundary; it is not a certification or a completed production security program. Requirements below explicitly distinguish implemented controls from gates for a pilot.

## Implemented foundation

Cloud startup rejects local-token mode. Cognito JWT verification checks RS256 signature from configured issuer JWKS, expiration, issue time, subject, issuer, token purpose `access`, and app `client_id`. It fails closed on missing keys or failed key retrieval. Tokens expire after five minutes in the Terraform client. Offline verification does not instantly observe token revocation; immediate revocation requires a denylist or authorized upstream check before pilot. [AWS JWT verification guidance](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html).

Local bearer authentication requires an explicitly configured random token of at least 32 characters and local mode. Compose publishes only to loopback. Do not expose a local development instance through a tunnel. The worker is private, reachable only through the API security group in AWS and an internal Docker network locally.

Requests have byte and schema limits; finite numeric constraints reject invalid landmarks, and errors suppress submitted content. Worker transport uses a configured origin, ignores environment proxies and refuses redirects. There is no request-supplied URL or import path. Output is validated and language/signer mismatches are rejected. API/worker access logging is disabled in the provided commands to avoid sensitive paths/query strings. Do not add full request/response logging.

AWS resources have private compute/database subnets, no SSH ingress, explicit development tester CIDRs, TLS at ALB, private S3 with public access blocked, encryption and versioning, IMDSv2, roles and immutable ECR tags. Database SSL is enforced. Compute egress is broad through NAT in development; outbound restrictions and service identity remain pre-production work. The default API has no AWS data permissions. The worker only reads approved model/asset object prefixes and decrypts through S3.

## Threats and pilot requirements

| Threat | Required mitigation / validation |
|---|---|
| Cross-tenant session or asset access | app authorization + forced RLS under a non-owner role; ownership tests for every resource |
| Malicious or revoked model/artifact | approved registry record, digest verification, reviewed build, rollback and revocation checks |
| Video/landmark re-identification | minimize transmission; treat both as sensitive; purpose-based access and retention |
| GPU exhaustion or slow consumers | per-subject rate/concurrency, body/read timeouts, bounded streams and admission/load tests |
| False confident translation | independent evaluation, calibrated uncertainty/abstention, correction and human route |
| Likeness misuse | contributor grant scopes for recording/training/rendering/derivatives; withdrawal and royalty audit |
| Credential theft / CI misuse | short-lived OIDC, least privilege, protected environments, trusted workflow and pinned actions |
| Dependency or image compromise | clean builds, dependency lock/digest review, image scanning, SBOM and vulnerability gate; CI actions are pinned to verified commits |
| Unencrypted internal interception | service authentication and TLS/mTLS before production; private SGs alone are insufficient |
| Lost or leaked state/backups | encrypted access-controlled state, version recovery exercise, restricted backups and deletion policy |

## Data lifecycle

Live video, audio, landmarks and transcripts are not persisted by the foundation. A research bucket is reserved for separately consented collection and has a seven-day expiration rule. This lifecycle is an eventual cleanup aid, not an exact deletion SLA, and noncurrent versions may remain for an additional period. Withdrawal jobs must explicitly delete all relevant versions and derived artifacts when required. Never rely on delete markers alone.

Consent grants are immutable records scoped to purpose, language, permitted use, document version and expiration. Training, inference, likeness rendering and public distribution are separate grants. A person's participation does not imply consent to all purposes. Rights review must clear the source dataset, model code, model weights, recordings, motion, identity/likeness and derivatives.

Withdrawal flow: authenticate contributor → freeze affected asset/model/signer for new use → trace dependent datasets/models/renders → revoke registry and media access → delete/replace derived assets according to rights agreement → invalidate caches/CDN → retrain or retire affected model where required → reconcile royalties → record evidence. Retain minimal audit metadata under an agreed retention policy. Data/ML lead must decide whether a model can lawfully remain in use; technical unlearning is not assumed solved.

Metadata retention proposals: session operational metadata 30 days; content-free telemetry 14 days; approved artifacts while rights remain valid; consent/royalty/audit retention set by appropriate professional advice and contributor agreements. These policies are design proposals; a scheduled deletion implementation is not supplied. Backups need a documented expiry and restore-time reapplication of deletion/withdrawal records.

## Authorization roles

User: own sessions and corrections. Contributor: own consent/likeness records and withdrawals. Deaf language reviewer: scoped lexicon/evaluation review. ML engineer: candidate models without sole promotion authority. Data steward: provenance/withdrawal administration. Platform engineer: infrastructure without unrestricted research content access. Organization administrator: membership and policy. Break-glass production access must be time-limited and audited.

The SQL migration enables forced row-level security using a server-set tenant context. The application must acquire a verified membership first and use `SET LOCAL` within each transaction, never a user-selected tenant header alone. RLS must be tested using a non-owner, non-BYPASSRLS role. The foundation HTTP endpoints do not yet use this database or claim tenant resource authorization.

## Human support and deployment claims

The initial bounded demo is not approved for consequential decisions. A human option is only available after a real partner workflow and availability test. The UI must show uncertainty and let the user stop, correct or request help. No unsupported compliance or accuracy claim is implied by using AWS encryption or Cognito.
