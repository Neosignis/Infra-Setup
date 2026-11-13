# Infrastructure and publication runbook

This repository has not been deployed. Commands below are deliberate operator steps. Confirm account, region, budget, GitHub owner and DNS before creating resources. No AWS keys belong in this repository or Terraform variables.

## Local setup

Install Docker with Compose and Terraform >=1.10,<2.0 through the team's approved package path. Python 3.12 runs the foundation directly without Docker. The validation report records which tools actually ran during creation. Dependencies are pinned at the top level; generate and review a complete transitive lock and digest-pinned base image before production. Docker currently uses `python:3.12-slim`, a mutable base tag.

Use `.env.example`, set a random development token, and run `docker compose up --build`. Keep host binding on `127.0.0.1`. No data volumes are mounted and no capture is persisted. Models/assets need an explicitly reviewed provider/image and rights-cleared object storage; none are bundled.

## Terraform bootstrap

1. Sign in using AWS SSO or a temporary role. Verify identity with `aws sts get-caller-identity`; never paste credentials into chat.
2. Copy the bootstrap tfvars example and choose an account/region-specific globally unique state bucket name. Confirm the destination account.
3. From `infra/bootstrap`, run `terraform init`, `terraform fmt -check`, `terraform validate`, and `terraform plan -out=bootstrap.tfplan`. Review concrete resources and costs before apply.
4. Apply that saved plan. Bootstrap initially has local state; keep it private. After the state bucket exists, add an S3 backend block in bootstrap and migrate with `terraform init -migrate-state` using key `bootstrap/terraform.tfstate` and `use_lockfile=true`. Store/backup local bootstrap state securely until migration is confirmed. Never commit it.

Bootstrap KMS/state resources use `prevent_destroy`. App data buckets do not force deletion. Database deletion protection and final snapshots prevent casual destructive teardown. Do not disable those safeguards just to make a CI job pass.

## Development environment

```sh
cd infra/environments/dev
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
# Edit region, account-specific bucket and other confirmed values.
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive ../..
terraform validate
terraform plan -out=dev.tfplan
# Apply only the reviewed saved plan in the intended account.
```

Default plan: VPC/subnets/security groups and S3 gateway endpoint; S3/KMS assets; ECR repositories; Cognito; ECS cluster. No NAT, ALB, API task, RDS instance or GPU host. KMS, storage, identity, logs and other resources can still incur charges; zero compute is not zero cost.

Opt into API runtime only after publishing an image: set `enable_runtime=true`, regional ACM certificate, digest-pinned `api_image` and explicit tester CIDRs. Create a DNS record pointing your certificate's hostname to the ALB; DNS/ACM issuance is not automated here. The ALB-generated DNS name will not match your own certificate. The API starts in Cognito mode. Its health can pass while engine readiness remains unavailable.

For GPU: select an approved ECS GPU-optimized AMI for the region/instance architecture, verify GPU quota and capacity, select a CUDA/runtime-compatible reviewed image, set `enable_gpu=true`, `worker_image`, `gpu_ami_id` and `engine_provider`. Increase `gpu_desired_tasks` from zero deliberately. EC2 capacity provider scales hosts for pending tasks. GPU instances, EBS, NAT and logs cost money even when no user is signing. After tests, set tasks back to zero and verify ASG hosts terminate; cooldowns and deployment overlap can delay shutdown. Check the AWS console/cost reporting; do not assume zero desired tasks means immediate zero cost.

For PostgreSQL: `enable_database=true` provisions private PostgreSQL 16 with AWS-managed master secret and seven-day backup retention. Apply the migration through a separately authorized job inside the VPC, using SSL verification and a migration role. The API is not wired to it yet. Create restricted application roles, secret access and rotation integration before session work. Never give application tasks the master password.

## GitHub publication

GitHub CLI was not authenticated at initial inspection; no remote repository has been created. After the owner is confirmed and the user signs in through `gh auth login`, the authorized publication path is:

```sh
git init -b main
git add .
git diff --cached --check
# Inspect staged file list for confidential material, data, state and credentials.
git commit -m "Establish engine-first Neosignis architecture and foundation"
gh repo create OWNER/neosignis-engine --private --source=. --remote=origin --push
```

Replace `OWNER` with the confirmed account/organization. Assign real CODEOWNERS and branch protection after publication. Do not use a guessed owner or public visibility. No attachments or raw reference screenshots are copied into this repository.

## CI and image publication

`ci.yml` runs Python tests, checks the generated OpenAPI, builds Docker, validates Compose, applies the PostgreSQL schema against a throwaway service, and runs Terraform fmt/validate without AWS credentials. CI does not apply Terraform.

`publish-image.yml` is manually dispatched from `main`, uses protected environment `development`, and publishes the foundation image tagged by Git commit to the selected API or worker ECR repository. It is build/push only, not a deployment. For real model images, extend the build to install approved model provider dependencies; the foundation worker has none.

Set GitHub environment variables `AWS_REGION`, `AWS_PUBLISH_ROLE_ARN`, `ECR_API_REPOSITORY` and `ECR_WORKER_REPOSITORY`. Repository values are repository names such as `neosignis-dev/api`. Configure an AWS OIDC provider for `https://token.actions.githubusercontent.com` with audience `sts.amazonaws.com`, then a publish role whose trust allows exactly `repo:OWNER/REPO:environment:development`. Environment protection must restrict deployments to `main` and require appropriate reviewers. [GitHub OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

`infra/policies/github-publish-trust.json.example` and `github-publish-permissions.json.example` are reviewable templates. Replace placeholders; creating/attaching that role is not automated here. The role can obtain an ECR login token and push only the two named repositories. It has no Terraform, ECS deploy, IAM administration or data bucket permissions. OIDC provider creation is account-global; reuse an existing provider rather than creating duplicates.

## Promotion and recovery

Build once, scan, record the image digest and test evidence, then update Terraform to that digest. Never deploy `latest`. Keep application and model digests in a release record. API rollback selects the previous task/image digest; model rollback also validates current rights, language and evaluation approval. A withdrawn model is not a valid rollback target.

Production requires a distinct account/root, stronger network egress, multi-AZ choices, membership/RLS enforcement, internal service authentication, WAF/rate controls, complete secrets/rotation, artifact signatures, tracing, alert routing, backup/restore exercises and a reviewed model/data release. The current dev root must not be described as production-ready.
