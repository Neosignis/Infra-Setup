# Neosignis engine foundation

Build and validate ASL sign-to-text first, then a validated response-to-sign path. Add Zoom and other channels after the engine passes evaluation. Nigerian Sign Language (NSL) is a separate language pack with its own data, models, reviewers, and release gate.

This repository contains the system architecture and an executable engineering foundation. **It does not contain a trained sign-language model, a signing avatar, or a working interpreter.** The API and worker return an explicit unavailable response until approved providers are installed. Infrastructure has not been deployed.

## Start here

0. [Run the local camera demo](docs/local-demo.md): setup, recording, export and acceptance checks.
1. [Architecture](docs/architecture.md): boundaries, diagrams, stack, AWS design, scaling and tradeoffs.
2. [First engine and model strategy](docs/engine.md): recognition, sign generation, realistic avatars, and evidence gates.
3. [Delivery plan](docs/delivery-plan.md): work packages, ownership and acceptance criteria.
4. [Infrastructure runbook](docs/infrastructure.md): Terraform, Docker, GitHub and AWS setup.
5. [Current implementation status](docs/status.md): tested work, planned work and unresolved decisions.
6. [Requirements and source review](docs/requirements.md): supplied references versus the current request.

## Repository

```text
apps/workbench/             React/TypeScript local camera capture and review app
src/neosignis/              API gateway, worker, typed contracts and provider interfaces
contracts/                 generated OpenAPI and streaming design
db/migrations/             PostgreSQL foundation schema
infra/bootstrap/           state storage bootstrap
infra/environments/dev/    independently managed development environment
infra/modules/             network, storage, registry, identity, API, database and GPU
ml/                        language packs, artifact and evaluation specifications
tests/                     API, authentication, provider and contract tests
scripts/                   reproducible checks and OpenAPI export
.github/workflows/         CI and manual image publication
docs/                      architecture, security, operations and team delivery
```

## Run the camera workbench (no AWS or Docker)

Use Python 3.12, Node.js 24 and a recent Chrome/Edge browser. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix apps/workbench ci
.venv/bin/python scripts/run_local_demo.py
```

Open `http://127.0.0.1:5173`. The launcher starts the workbench, API and worker on loopback, creates an ephemeral development token, and stops the services on Ctrl+C. It does not use AWS credentials. The camera app records and exports local evaluation clips; **it does not recognize signing or play signed responses yet**. Full setup and review checklist: [local demo guide](docs/local-demo.md).

## Run the API foundation separately

Use Python 3.12. Docker is optional for the Python-only path.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Set DEV_API_TOKEN to a random value of at least 32 characters.
# For example generate it with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
docker compose up --build
```

The API is bound to `127.0.0.1:8000`; the worker is not published to the host. Docker Compose reads `.env`. Without Docker, export the values from `.env` in your terminal, set `INFERENCE_URL=http://127.0.0.1:8001`, and run these in separate terminals:

```sh
.venv/bin/python -m uvicorn neosignis.worker:app --app-dir src --host 127.0.0.1 --port 8001
.venv/bin/python -m uvicorn neosignis.api:app --app-dir src --host 127.0.0.1 --port 8000
```

`GET /healthz` checks process health. `GET /readyz` checks whether approved engine providers are available and returns **503** in the default configuration. `GET /v1/capabilities` requires authentication and explains capability availability. OpenAPI is checked in at [contracts/openapi.json](contracts/openapi.json); interactive docs are available locally at `/docs`.

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python scripts/export_openapi.py --check
```

The local token is for the development workbench only. Cloud configuration requires Cognito access tokens; development token authentication cannot start with `APP_ENV=cloud`.

## Cloud and publication

Read the runbook before applying Terraform. The default development environment creates foundation resources only; API, database, GPU capacity and NAT are opt-in. This is cost containment, not a cost guarantee. No cloud deployment or GitHub repository creation occurs as part of a local test.

The source repository is [Neosignis/Infra-Setup](https://github.com/Neosignis/Infra-Setup). Keep raw recordings, confidential source documents, credentials and contributor identity records out of Git history. Local capture exports are private working files; they do not establish training, distribution or likeness rights.

All rights reserved pending the team's software license decision. Dataset, model, likeness and motion licenses are independent of the source-code license.

The [ASL model options](docs/model-options.md) identify concrete research, owned-data and licensed-provider paths and the evidence required before selection.
