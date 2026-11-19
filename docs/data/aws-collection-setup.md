# AWS dataset collection setup

17 November 2026: user-supplied account `324793866495`, region `us-east-1`, Free plan and $100 credit. Billing and live resources are unverified. The startup-credit application is pending.

## Connect Antigravity's terminal

The local CLI is 2.31.18. The old SSO profiles point to another account and are expired. Console/CloudShell login does not sign in this Mac. The supplied console link also reached a sign-in page in the available browser. No cloud resources were listed or changed.

1. Update using the [official macOS AWS CLI installer](https://awscli.amazonaws.com/AWSCLIV2.pkg). In a new terminal, `aws --version` must show 2.32.0 or newer for browser-based login.
2. Run these commands, completing browser login yourself. Choose the Neosignis account:

```sh
aws login --profile neosignis-login --region us-east-1
aws sts get-caller-identity --profile neosignis-login --region us-east-1 --query Account --output text
```

The account-only output must be **324793866495**. Stop if it differs. Prefer an IAM identity for project operations. IAM identities need `SignInLocalDevelopmentAccess` for login, plus separate permissions for their work.

For Terraform/SDK compatibility, use a process-credential profile:

```sh
aws configure set credential_process 'aws configure export-credentials --profile neosignis-login --format process' --profile neosignis
aws configure set region us-east-1 --profile neosignis
aws sts get-caller-identity --profile neosignis --query Account --output text
```

Do not run `export-credentials` alone and paste credentials. No passwords, keys, codes, tokens or credential-cache files belong in chat/GitHub. References: [AWS browser login/SDK compatibility](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html), [CLI installation/update](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

## Prepared configuration

The independent [dataset root](../../infra/environments/datasets/main.tf) defines two private versioned S3 buckets: datasets and restricted identity/permission records. They have separate KMS keys, TLS-only access, protection against encryption overrides and deletion safeguards. Completed files/versions do not expire automatically; only abandoned multipart uploads are cleared after seven days. Retention and withdrawal procedures still need implementing.

Four IAM policies are prepared but **unattached**: intake writes `incoming/`; reviewers process/promote recordings; training reads `approved/` only; rights operators access `records/` in the separate bucket. No users, trusted roles or attachments are guessed. These policies do not restrict an existing administrator or constitute an approval system.

Optional account-wide $25 monthly alerts track usage before credits, at 50%, 80% and 100%. The example leaves the email blank, which creates no alerts. The amount is a draft alert threshold, not a hard cap. No VPC, NAT, application server, database or GPU is included.

```text
datasets/incoming/<clip-id>/           unapproved submissions
datasets/review/<clip-id>/             technical/linguistic review
datasets/approved/releases/<version>/  approved media/features/manifests
rights/records/<permission-id>/        restricted permissions/identity mapping
```

Prefixes appear when objects are uploaded. Upload links/UI, review workflows, independent backup, training loaders and models are not implemented by Terraform. Versioning is recovery within a bucket, not an independent backup. Existing seven-day `research` storage must not hold the permanent corpus.

## Validation and deployment order

Mocked tests create nothing in AWS:

```sh
terraform -chdir=infra/environments/datasets init -backend=false -input=false
terraform -chdir=infra/environments/datasets validate
terraform -chdir=infra/environments/datasets test -no-color
```

After local login works:

1. Verify STS identity, Free-plan service availability, existing storage/state and budgets. Do not automatically upgrade the plan or create duplicate resources.
2. Choose the alert address and confirm the draft threshold. The backend example is a proposed state bucket, not a verified existing bucket.
3. Prepare/review the [state bootstrap](../infrastructure.md#terraform-bootstrap) if needed. Verify identity separately: the datasets account guard does not guard bootstrap. Keep local state private and migrate it as documented.
4. Copy the datasets tfvars/backend examples locally, set verified backend details and email, then generate a real plan:

```sh
cd infra/environments/datasets
cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl
AWS_PROFILE=neosignis terraform init -reconfigure -backend-config=backend.hcl
AWS_PROFILE=neosignis terraform plan -out=datasets.tfplan
```

5. Review actual resources, cost and permissions before applying. Review role trust/attachments separately. Implement scoped upload links and validation, then test private synthetic upload, encryption, retrieval and version recovery before contributor recording.
6. Import a small permitted sample, record provenance/licences/checksums, obtain linguistic review and freeze signer-disjoint splits before training. The [source register](../../ml/data/source-register.json) remains a candidate list, with nothing downloaded or approved.

Keep recordings, identity/permission records, state and credentials outside Git. Arrange an independent private backup and export/transition before Free-plan expiry. Do not join Organizations just to enable SSO: [AWS lists it as an automatic Paid-plan transition](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html).
