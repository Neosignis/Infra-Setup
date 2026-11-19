# Architecture plan review and change report

**16 November 2026 — comparison against the actual Neosignis checkout and current agreed direction**

Input: `Neosignis System Architecture and Delivery Plan.md_1`, Version 1.0 dated 13 November 2026. Reviewed code: `Neosignis/Infra-Setup`, feature commit `4b2d33ab271cf3d9fca9b4248dd2dc25e2782b71`. Main remains at `3dd716e5b864dbef001e57f38e48c0b242122e7f`; draft PR #1 is open/unmerged. This is a code/document review, not an AWS account inventory or a linguistic model evaluation.

The source is useful as a description of intentions, but **it cannot be used as the implementation handoff for this repository**. Its four-service tree, rule-based translation, authentication, endpoints, provisioning and deployment switches largely describe another/unprovided implementation. They may exist elsewhere; no matching source or execution evidence was supplied here. The revision replaces those claims with inspected facts and marks future work explicitly.

## Severity and disposition

- **Critical:** could materially misrepresent the engine or direct work/deployment against a nonexistent capability.
- **High:** affects correctness, data retention, security, delivery dependencies or acceptance evidence.
- **Medium:** unsupported assumptions, stale descriptions or maintainability/operations problems.

These are review priorities, not a claim that a deployed system has been exploited. A corrected document does not mean every identified engineering gap has been fixed in code.

## Findings and how Version 2.0 addresses them

| ID | Priority | Source section / claim | Evidence and concern | Revision |
|---|---|---|---|---|
| R01 | Critical | §§3–6, 12: four working services, translator and manifest renderer | `src/neosignis/api.py`, `worker.py`, `providers.py` and `compose.yaml` supply an API and provider host. No translation-engine/render-service implementations exist in the reviewed tree. | Replaced catalogue and flows with two runtime units and explicit missing models/planner/rendering. |
| R02 | Critical | §4.1: a built English-to-ASL rules path | No such rules implementation exists. Deleting articles/be-verbs or moving words is not sufficient evidence of ASL grammar even if implemented. | Removed working-translation claim; distinguishes exact complete reviewed responses from learned/evaluated language planning. |
| R03 | High | §§4, 6, 10: `X-API-Key`, API keys outside development | `auth.py` implements local bearer tokens and Cognito access-token verification; cloud rejects local dev mode. No X-API-Key scheme exists. | Corrected current authentication and retained production login/authorisation gaps. |
| R04 | High | §§4–6: alternate endpoints, HTTP 501 and 10 MB audio | OpenAPI exposes `/v1/capabilities`, `/v1/recognize`, `/v1/render`, `/healthz`, `/readyz`; absent capability returns 503. No audio route; body limit is 4 MiB. | Replaced route/status/input table with actual contract. |
| R05 | High | §§4.2, 8, E4: hand/body features already extracted; face omitted | `contracts.py` supports 33 pose + 21 + 21 hand + 478 face points. No browser extraction exists. Ignoring non-manual grammar conflicts with the intended product. | Documents 553-point schema with nullable groups and model-specific preprocessing; extraction remains future work. |
| R06 | Critical | §§4.3, 7: resources described as provisioned | No real AWS plan/apply or account inventory is verified. RDS/runtime/GPU are opt-in; no SQS module or `renders` bucket exists. | Separates code-defined, proposed and cloud-unverified resources throughout. |
| R07 | High | §7: no schema; defer first consent/provenance migration | `db/migrations/001_foundation.sql` already provides consent/assets, datasets/models, lineage, evaluations, sessions, withdrawals and render usage with tenant RLS. | Preserves/refines existing schema; application workflows, approvals, deletion and royalties remain missing. |
| R08 | High | §7 and E3: put training clips in general asset storage without a durable corpus plan | `storage/main.tf` has a research bucket with seven-day expiry and no dedicated dataset boundary; uploader/review services absent. | Adds durable datasets, restricted rights/identity records and ingestion/annotation before distributed collection. |
| R09 | Medium | §§5, 9.5: shared JSON telemetry, `/metrics`, CORS, Sentry and complete alarms | Shared helper provides body limits/content-free validation errors, not that telemetry stack. Some Terraform logs/alarm definitions exist, not full instrumentation/routing. | Lists monitoring and alert ownership as implementation gates instead of completed controls. |
| R10 | High | §§9.4, 11, 12: 61 tests; nine local smoke checks; CI never run | Current suites differ. Local review passed 54 Python and 26 frontend tests plus build/OpenAPI/repository checks. Feature CI passed application/workbench/Terraform jobs, including five browser tests. | Gives suite-specific dated evidence and distinguishes fake camera/fixtures from real ASL evaluation. |
| R11 | Critical | §§9, E1: bootstrap creates OIDC/ECR; deploy switches launch four images | Bootstrap creates state/KMS storage only. Manual `publish-image.yml` builds API/worker foundation images on main; it does not deploy. `AWS_DEPLOY_ENABLED`/`deploy_services` do not exist. | Removes unusable recipe; links actual infrastructure runbook and defines future CD separately. |
| R12 | High | E1 steps 8–9: test cloud endpoint, then add HTTPS/restrictions | Runtime Terraform already requires certificate, digest image and tester CIDRs. Remote content must not precede secure access setup. | Makes TLS/hostname and access restrictions prerequisites to remote testing. |
| R13 | High | §§5, 9.1: readiness/metrics/docs blocked by ALB | API ALB default action forwards all paths; gateway FastAPI exposes docs/OpenAPI. No relevant path allowlist/deny policy exists. | Identifies a real hardening gap; does not falsely claim the filter was added by this documentation revision. |
| R14 | High | §§9.5, 10: secrets can never enter Terraform state | That cannot be guaranteed by Secrets Manager or `sensitive` flags alone. Current RDS uses managed master credentials, but future secret wiring needs review. | Replaces absolute assurance with explicit managed-secret/state controls and primary HashiCorp guidance. |
| R15 | Medium | §§9.2–3: shared composition, staging/prod roots and selected `us-east-1` | Only `infra/environments/dev` exists; region is an input. Dev has one API task, optional single-AZ RDS and optional single NAT, not production HA. | Marks account/region/environment/HA choices as unresolved and separates implemented dev topology. |
| R16 | High | §§2, 8–9: GPU module deferred; scale-to-zero and instant live path assumed | GPU module already exists. Zero desired tasks/capacity is not a verified request wake-up or cold-start latency policy. CPU-only cloud worker module is absent. | Documents actual GPU scaffold, worker discovery dependency, warm/cold benchmarks and hosting decisions. |
| R17 | Critical | §§12.2–6: cloud/ASR first; recognition months later; critical path is output-only | Conflicts with user's engine-first/sign-to-text priority. Head of ML hire and provider selection were assumed dependencies, not agreed staffing. | Reorders data/preprocessing → real recognition → two-way response; cloud is a parallel need-based track; identifies real linguistic-review dependency. |
| R18 | High | E3: 100 isolated signs/20 sentences and replacing rules validate a language pack | Those numbers/protocols are unagreed; an asset list or reviewed vocabulary does not approve arbitrary sentence grammar or a whole language. | Uses scoped, versioned approvals, independent references/holdout and a continuous-translation gate distinct from bounded classification. |
| R19 | High | E4 exit: publish accuracy and choose an abstain rule | No sample/signer counts, unknown-input criteria, coverage or pre-agreed threshold; refusing everything could look accurate. | Adds explicit quality/coverage/false-accept/latency proposals, review ownership and locked evaluation requirements; actual acceptance file stays unapproved. |
| R20 | High | §§2, 6, 8: one manifest never changes; renderers all output that contract | Current rendering result is an asset descriptor, not a timeline. Capture, meaning, motion and delivered media have different information needs. | Uses versioned layered contracts and adapters; rich sign plans remain proposed. |
| R21 | High | §§4.4, E5: defer rights/royalty design; low confidence offers a human | Schema exists, but permission/use enforcement and human dispatch do not. A general `validated` flag is not runtime approval. | Rights/provenance before collection, registry enforcement before release, actual partner availability before a human option is advertised. |
| R22 | Medium | §§8.2, E6: Zoom always requires server rendering; integration after output alone | Adapter/media architecture and SDK permissions are not proven here; an output-only bot does not meet the bidirectional goal. | Requires relevant recognition/output gates and current transport/policy spike; no universal server-rendering assumption. |
| R23 | Medium | §§12, appendix: named files/tree and calendar | `services`, `packages`, `web`, `infra/terraform`, `ml/README.md`, `docs/HOW-IT-WORKS.md` and cited bootstrap runbook are absent. `docs/STATUS.md` has wrong tracked case; macOS may resolve it while Linux will not. | Uses actual repository paths, separates proposed directories and replaces elapsed dates with dependency/evidence gates. |
| R24 | Medium | §13: competitor public API is still a first-mover opportunity | Latest public-source study found advertised API access; NSL data listings do not prove a validated NSL interpreter either. Market assumptions should not be release dependencies. | Keeps independently evaluated language depth, contributor-specific style/rights and human support as product hypotheses; no unverified market lead claim. |
| R25 | High | New finding in our own foundation: frame/schema limits versus body limit | A compact 300-frame full-feature request is 4,331,796 bytes, above the 4,194,304-byte middleware limit. Formal frame count does not ensure usable full-size transport. | Adds a measured blocker and selected-wire-format regression gate. No runtime limits were silently changed. |

## Useful ideas retained

Engine-first/channel independence; clear unavailable/abstain states; separate language evidence; community involvement; licensed/consented data; replaceable rendering; measured P50/P95 latency; reproducible images/infrastructure and gated delivery. Hosted ASR and a sign-sequence plan are reasonable future candidates, not present implementations or proof of ASL correctness.

## Where our existing documentation also needed correction

The reviewed checkout's own `docs/status.md`/`docs/validation.md` still described feature CI as pending and older delivery notes referenced an elapsed November 13–15 target and an unconfirmed repository. The component table still called the camera app unimplemented. This review updates those descriptions and directs readers to Version 2.0. It does not conceal the current payload, storage, approval, telemetry or authorisation gaps.

## Milestone migration

| Source milestone | Reviewed disposition |
|---|---|
| E0: foundation with working text-to-manifest | E0 engineering foundation only; no text-to-sign implementation verified |
| E1: live AWS before engine | Parallel C0 durable-data storage / C1 shared runtime only when needed |
| E2: speech to gloss timeline | Optional speech adapter after typed response path is meaningful |
| E3: isolated signing output | E4 complete reviewed-response loop; skeleton remains optional diagnostic |
| E4: recognition in months 2–4 | E3 first real model milestone after rights/data/exact preprocessing |
| E5: avatar decision | E6 evidence-led realistic signer comparison; preserve comprehension and contributor rights |
| E6: channel after output | E8 after relevant recognition/output and pilot safeguards |

New E1/E2 make data rights, collection, annotation, split policy and exact preprocessing explicit. New E5 distinguishes continuous translation from a small label classifier; E7 covers operational and limited-pilot evidence.

## Verification performed on 16 November 2026

- Read the full supplied Markdown file and inspected actual gateway/worker/provider/auth/contract code, browser package, CI/publication workflow, database migration and Terraform roots/modules.
- Re-ran 54 Python tests, 26 frontend tests, TypeScript/production build, OpenAPI drift and repository checks successfully. No inference accuracy was measured.
- Rechecked GitHub main/PR state and [successful feature CI](https://github.com/Neosignis/Infra-Setup/actions/runs/43724239789). Its browser tests use a simulated camera; Docker/PostgreSQL checks run in CI. No new browser suite was needed for a documentation-only revision, and the user demo server was not stopped/restarted.
- Measured the synthetic transport fixture below. It tests bytes only, not model behaviour, linguistic content or capture quality.
- Did not inspect AWS credentials, inventory an AWS account, plan/apply cloud resources, download datasets, change runtime contracts, merge the feature branch or publish confidential source materials.

### Reproducing the payload finding

Run with Python from the checkout; no files, network or signing recordings are required:

```python
import json

point = {"x": 0.5, "y": 0.5, "z": 0.0}
frames = [
    {
        "t_ms": i * 33,
        "pose": [point] * 33,
        "left_hand": [point] * 21,
        "right_hand": [point] * 21,
        "face": [point] * 478,
    }
    for i in range(300)
]
payload = {
    "language": "ase",
    "feature_schema": "neosignis.landmarks.v1",
    "extractor_version": "payload-audit-fixture",
    "mirrored": False,
    "frames": frames,
}
size = len(json.dumps(payload, separators=(",", ":")).encode())
print(size, 4 * 1024 * 1024, size > 4 * 1024 * 1024)
# 4331796 4194304 True
```

This demonstrates a fully populated maximum-length shape that cannot traverse current middleware. It does not mean every request fails: fewer frames/groups or other transport choices may fit. Resolve the selected model's actual requirements and test representative precision/overhead before choosing a fix.

## Evidence references

Repository snapshot: [feature commit](https://github.com/Neosignis/Infra-Setup/commit/4b2d33ab271cf3d9fca9b4248dd2dc25e2782b71), [draft PR #1](https://github.com/Neosignis/Infra-Setup/pull/1).

Inspected paths: `src/neosignis/{api,worker,auth,providers,contracts,http_common}.py`; `contracts/openapi.json`; `compose.yaml`; `apps/workbench/`; `db/migrations/001_foundation.sql`; `.github/workflows/{ci,publish-image}.yml`; `infra/bootstrap/main.tf`; `infra/environments/dev/`; and `infra/modules/{network,storage,api,database,gpu}/main.tf`.

External primary checks: [HashiCorp: sensitive values/state](https://developer.hashicorp.com/terraform/language/manage-sensitive-data), [AWS: GPU task requirements and Fargate limitation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters-managed-instances.html). Competitor/data conclusions are dated in `docs/research/2026-11-15-engine-and-data-plan.md`; exact rights and SDK policies must be rechecked when acquiring/integrating them.
