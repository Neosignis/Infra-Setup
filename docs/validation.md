# Validation report

Observed on 13 November 2026. No trained model, avatar or cloud deployment has been tested.

| Check | Result | What it establishes |
|---|---|---|
| Python unit/in-process API tests | **32 passed** | JWT purpose/client/issuer/expiry/signature checks; local/cloud safety; bounded inputs; timestamp rules; content-free errors; absent models; language/signer/version separation; cancellation/admission behavior |
| Real loopback gateway → worker HTTP smoke | **Passed** | liveness 200; authenticated capabilities list ASL/NSL as disabled; readiness 503; unauthenticated API 401; temporary processes stopped |
| Generated OpenAPI drift check | **Passed** | checked-in HTTP schema matches executable gateway |
| Terraform recursive formatting | **Passed** | canonical HCL formatting |
| Bootstrap Terraform validate | **Passed** | provider schema/configuration validity, without an AWS plan/apply |
| Development Terraform validate | **Passed, no warnings** | all referenced module configurations valid against the installed provider |
| Terraform mocked plan tests | **4 passed** | default excludes runtime/RDS/GPU; incomplete runtime/GPU configurations rejected; optional API/RDS/GPU full path plans with concrete mock inputs |
| JSON, Python syntax and Markdown local links | **Passed** | structured files parse and local documentation targets exist |
| Compose/workflow YAML parse | **Passed** | YAML structure parses; not a Docker or GitHub Actions execution |
| Terraform binary integrity | **Verified** | official Terraform 1.14.0 darwin_arm64 SHA256 matches downloaded archive |
| Provider installation and locks | **Verified** | AWS provider 6.73.0 installed with HashiCorp signature; generated registry lock/checksums retained in both roots |
| GitHub Actions references | **Pinned** | five official release tags resolved through GitHub's API to immutable commit SHAs |
| Git ignore safeguards | **Passed** | `.env`, virtualenv, `.terraform`, state and plan paths are ignored |
| Docker build / Compose runtime | **Not run locally** | Docker absent; executable checks supplied in CI |
| PostgreSQL migration / non-owner RLS | **Not run locally** | PostgreSQL absent; real PostgreSQL 16 migration/isolation checks supplied in CI |
| GitHub Actions run | **Not run** | repository not published/authenticated |
| Real AWS plan/apply, credentials, quota, TLS/DNS and GPU runtime | **Not run** | account/region/budget/domain unconfirmed; no resources created |
| Real ASL recognition / signed response / avatar comprehension | **Not run** | no model, data, signer assets or reviewers supplied |

Commands used for the main checks:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/smoke_local.py
PYTHONPATH=src .venv/bin/python scripts/export_openapi.py --check
.venv/bin/python scripts/check_repository.py
terraform fmt -check -recursive infra
terraform -chdir=infra/bootstrap validate
terraform -chdir=infra/environments/dev validate
terraform -chdir=infra/environments/dev test
```

Terraform 1.14.0 was run from a temporary verified binary because it was not installed globally. Provider validation required permission for a local plugin socket outside the execution sandbox; mocked tests used no AWS APIs. The Python virtualenv reused matching preinstalled framework versions and installed JWT/cryptography/HTTP client dependencies locally. A clean Docker build remains necessary to prove container dependency resolution.

The PostgreSQL and Docker CI steps have been authored but not executed on GitHub. Passing the checks above does not imply those steps will pass until run. API tests use clearly isolated fixtures to validate engineering behavior; they do not measure sign-language accuracy or supply a demo provider.
