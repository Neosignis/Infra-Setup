# Delivery plan and team handoff

Work begins on Friday 13 November 2026 in Africa/Lagos time. The requested this-week target is an internal bounded engine proof by Sunday 15 November if model/data/reviewer access is available. These are three delivery sessions, not an assumption that the team is staffed through the weekend. If that is not feasible, preserve the same order over the next three working sessions.

The architecture and foundation can be completed independently of a trained model. An actual sign-language engine and realistic avatar cannot be honestly promised for a fixed date without data, rights, suitable models and reviewer capacity.

## First three sessions

| Session | Owner role | Work and dependencies | Acceptance |
|---|---|---|---|
| 1 — foundation and scope | Technical lead + platform + Deaf ASL lead | agree domain/phrase set, rights, test split and targets; validate repository; select region/budget; set GitHub ownership | reproducible local boot, CI passing, frozen demo/evaluation plan, named model/data path |
| 2 — inbound engine | ML lead + web engineer | integrate approved ASL model; implement versioned capture and preprocessing; held-out signer collection | camera signing produces measured text; negatives abstain; no scripted labels; report errors/latency |
| 3 — response and demonstration | avatar/motion engineer + Deaf reviewers + ML/web | exact reviewed response set; consented clips first or validated rig if already available; run independent review | signer → text → typed response → comprehensible signed output; renderer honestly labelled; evidence and limitations recorded |

Do not let AWS setup block local inference. Provision cloud only when a measured local model needs shared or GPU execution. Do not let avatar asset production block inbound recognition.

## Work packages

| ID | Accountable role | Components / tasks | Dependencies | Done when |
|---|---|---|---|---|
| WP01 | Technical lead | architecture, ADRs, requirements, boundaries, review decisions | current materials | team review resolves key decisions and records exceptions |
| WP02 | Platform engineer | Terraform bootstrap, identity, ECR/S3, private network, cost alerts | AWS account/region/budget | fmt/validate/plan and approved apply; security checks; no unexpected running GPU |
| WP03 | Platform + backend | CI, image build, digest release, Cognito auth | GitHub auth/owner; WP02 | private repo, branch protection, build and auth smoke test |
| WP04 | Deaf ASL lead + data steward | paid reviewers, scope, data collection/consent/provenance, holdout | contributors and rights | approved scope and auditable signer-independent splits |
| WP05 | ML lead | model selection, adapter, calibration, quality/error evaluation | WP04 + checkpoint | G1 report and capability only enabled for approved scope |
| WP06 | Web engineer | camera workbench, tracking, capture quality, correction and accessibility | input contract + WP05 | camera-to-text loop tested with real signer, mirrored camera handled correctly |
| WP07 | Motion/rendering engineer | reviewed response mapping, asset retrieval, signer output | consented assets + Deaf review | G2 comprehension report; unsupported text rejected |
| WP08 | Backend engineer | durable sessions, streaming epochs, quotas, authorization, registry enforcement | WP05/WP06 + DB migrations | reconnect/order/backpressure/ownership tests pass |
| WP09 | Data steward + backend | opt-in, withdrawal, deletion jobs, lineage and royalties | rights schema + policies | withdrawal reaches artifacts, caches and dependent releases |
| WP10 | ML + Deaf NSL lead | NSL corpus and language-specific model/evaluation | independent local partnership | separate NSL gate passes; no ASL substitution |
| WP11 | Rendering engineer | realistic rig or neural human backend | G2, rights, suitable motion | G3 passes before a realism claim |
| WP12 | Platform + QA | load, recovery, observability, cost and security controls | implemented engine | bounded internal pilot passes G4 |
| WP13 | Integration engineer | Zoom/Teams/LiveKit/LMS feasibility then adapter | engine gates first | current policies checked and G5 passes |

Roles are assignments to fill, not claims of available staff. Initial parallel ownership can be combined in a small team; language review remains a distinct paid competency.

## GitHub work structure

Use one private `neosignis-engine` repository initially. Protect `main` with required CI, PR review and no force pushes. Assign CODEOWNERS only after actual GitHub handles are known. Create labels `architecture`, `platform`, `backend`, `web`, `ml`, `data-rights`, `asl`, `nsl`, `rendering`, `evaluation`, `blocked`. Convert work packages into issues with owner, dependency, acceptance and evidence links. Keep raw data, model weights, personal information and supplied confidential screenshots outside GitHub.

Use small PRs and explicit schema/API version changes. Model and language-pack promotions are independent from application releases; each pins a digest and evaluation report. Development deployments use a protected GitHub environment. Production is not enabled by a directory name or CI success alone.

## Review decisions

ASL first is confirmed. The following remain required before cloud deployment or model release: GitHub owner/authentication; AWS account, region and budget; selected model and all rights; bounded demo vocabulary/domain; reviewer availability and acceptance thresholds; first signer assets and renderer choice. The local engineering foundation proceeds while these are pending.

## Migration strategy

No legacy implementation is present locally. Do not perform any destructive cloud migration on that basis. If old repositories or services are supplied, inventory resources/data/credentials, take a verified backup, map the old API and schema, and run the new service alongside it. Use additive migrations and versioned adapters, compare outputs on consented test traffic, then switch a limited cohort. Retain rollback until quality, data integrity and recovery checks pass. No production data import is part of this foundation.
