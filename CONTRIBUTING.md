# Contributing

Read the architecture, delivery plan and current status before taking a work package. Use Python 3.12 and a virtual environment. Run tests and the OpenAPI drift check before a PR. Terraform changes require fmt/validate, a local mocked plan test, and a real saved plan in the intended account before apply.

Keep providers independent of channel SDKs. A new capability needs rights, immutable artifact metadata, real evaluation, explicit scope and reviewer sign-off. Test fixtures must stay under `tests/`; never install them as providers for a demo. An unavailable model must remain visibly unavailable.

Do not commit raw signing/video/audio, model weights, avatar identities, secrets, Terraform state/plan files or confidential reference documents. Keep `.env` private. Document schema/API version changes and update generated OpenAPI. Use additive database migrations with a migration role and non-owner RLS tests.

CI actions are pinned to verified commit SHAs. Review updates and configure dependency update automation before production. Assign CODEOWNERS to real team handles after GitHub ownership is known. Protect main with CI and review; no automatic infrastructure apply is supplied.
