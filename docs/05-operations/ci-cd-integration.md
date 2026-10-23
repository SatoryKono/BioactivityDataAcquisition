______________________________________________________________________

Version: 1.0.3
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-10-16'

______________________________________________________________________

# CI/CD Pipeline Integration Guide

**Issue:** #6554
**SSOT map:** [ci-workflow-map.md](ci-workflow-map.md) (52 legacy workflows and their replacement status)
**Also:** [github-local-workflow.md](../03-guides/github-local-workflow.md)

## Overview

<!-- policy-anchor:deployment-provider -->
Pull-request coordination runs in GitHub Actions (`deployment.provider=github_actions`, `.github/workflows/pr-required.yml`). `.circleci/config.yml` remains in the tree and is not current merge protection. Local-Only product runtime does not require cloud deployment.

<!-- policy-anchor:ruleset-enforcement-mode -->
Rulesets `13643213` and `15730586`, the ones that include `refs/heads/main`, are `enforcement: disabled` on the 2026-10-16 read-only GET. <!-- policy-anchor:stored-ruleset-contexts --> They still store `ci/circleci: pr-gate-complete` (the companion also stores `ci/circleci: root-hygiene`). A stored context is not active CircleCI protection and is not configured GitHub Actions enforcement. <!-- policy-anchor:target-gha-context --> The target job name `pr-gate-complete` is not the context stored on those rulesets. <!-- policy-anchor:enforcement-verified-date --> Catalog `enforcement_verified_date` `2026-10-09` is not proof of active merge protection. <!-- policy-anchor:merge-block --> A successful `pr-gate-complete` does not by itself block merge, because classic branch protection is absent and those rulesets are disabled. An offline catalog match does not confirm live server rulesets. CodeQL is excluded from required checks by the owner decision in #11929.

## Current pull-request coordinator

`.github/workflows/pr-required.yml` is the runnable pull-request coordinator.
These four jobs are GitHub Actions jobs. They are not CircleCI jobs and not
typed `ci-lane` names.

| Job id | Job name | Role in the current coordinator |
| --- | --- | --- |
| `classify-changes` | Classify changes (decision matrix) | Marks each catalog gate `required` or `not_applicable` |
| `fast-governance` | Fast governance | Root hygiene, commit lint, documentation checks, required-check prose consistency, zizmor, dependency review |
| `class-lane` | Class lane | Selected steps for `lint-arch`, `tests`, `type-checking`, `security`, `docker`, `generated-artifacts`, and `duplication` |
| `pr-gate-complete` | pr-gate-complete | Fail-closed aggregate of `classify-changes`, `fast-governance`, and `class-lane` |

`class-lane` is created only when at least one of `lint-arch`, `tests`,
`type-checking`, `security`, `docker`, `generated-artifacts`, or `duplication`
is `required`. `fast-governance` and `pr-gate-complete` still run. A skipped
`class-lane` is not a CircleCI `test-fast` or `test-integration` job.

## Acceptance

Record the pull-request head SHA and the GitHub Actions run of workflow
`PR Gate Complete`. Checkout is chosen separately for each job.

| Job | Checkout on `pull_request` |
| --- | --- |
| `classify-changes` | `github.event.pull_request.base.sha`, or `github.sha` when that event field is absent. This is the base SHA. |
| `pr-gate-complete` | The same base ref as `classify-changes`. |
| `fast-governance` | `actions/checkout` with no `ref`. GitHub uses `refs/pull/<number>/merge`. |
| `class-lane` | The same default checkout as `fast-governance`. |

On run `38909556660` for head `3ccabb127f84c0e3a9d683dbc6bb594682f49386`,
`classify-changes` and `pr-gate-complete` checked out base
`40fa210b9279c5a10568783815230a8955cc1d02`. `fast-governance` and `class-lane`
checked out synthetic merge `4e39da041f29f57e6ba0d5ad75ccccae305c89a2`
(`refs/pull/12234/merge`). That merge SHA is not the API head SHA. Accept the
run only from the conclusions of the four jobs above. A successful
`pr-gate-complete` does not by itself block merge. The README CI badge links
to a pipeline list and is not this gate.

## Historical CircleCI lane names

The names below are retained CircleCI jobs and typed `ci-lane` values from
`.circleci/config.yml`. They are not the current coordinator jobs.

| Lane | Historical CircleCI job or typed ci-lane | Purpose |
| --- | --- | --- |
| Architecture | `lint-arch`, `arch-tests`, `architecture-docs` | Layering, debt and generated documentation |
| Docs | `docs-governance`, `docs-kpi`, `skills-consistency` | Documentation and runtime mirror validation |
| Contracts | `dq-consistency`, `schema-governance`, `semantic-governance`, `port-contracts`, `provider-contract-drift` | Data and adapter contracts |
| Security/quality | `security-scans`, `mypy`, `duplication`, `root-hygiene` | Security and code quality gates |
| Docker | `docker-baseline`, `docker-publish` | Build and full baseline before separate publication approval |
| Release preparation | `release-validation` | Prepared wheel/sdist, install, tests, security and SPDX; remote acceptance and protected promotion pending |

Scheduled and manual lanes in that config use typed pipeline parameters on
main. The workflow map records actual run IDs, schedule registration, input
acceptance, disabled surfaces and unresolved parity. Do not treat a configured
historical lane as accepted until its required artifacts and terminal result
have been verified.

## Quality gates contributors hit most

1. Ruff / format (pre-commit)
2. Architecture + import-linter
3. Contract / schema governance
4. Docs link + MkDocs strict (docs changes)
5. Root hygiene allowlist

## Local parity

```bash
# examples — prefer project make/uv entrypoints when available
pre-commit run --all-files
python -m pytest tests/architecture -q
python -m scripts.docs check-links
```

## Badges and source identity

The README CI badge links to the main pipeline list; it identifies a provider
view, not the result of `.github/workflows/pr-required.yml`. The coverage badge
states the 85% policy. Use the head SHA and the four coordinator job
conclusions recorded under Acceptance. A project-wide badge can reflect a
maintenance workflow and must not be used as proof that the required PR gate
passed.

## Artifacts

- Test reports, coverage, diagram PNG artifacts (CI-only after DOC-GOV-02)
- Docs link-check JSON
- Do not commit `docs/site/` build output

## Secrets

- The current coordinator grants `contents: read`. Fast governance also grants
  `security-events: write`. The `docker-lane` job additionally grants
  `security-events: write`, `packages: write`, `id-token: write`, and
  `attestations: write` so the nested Docker workflow passes startup
  validation. Never commit tokens.
- `.env` files are machine-local and require explicit approval to edit.

### Historical CircleCI contexts

- Restricted CircleCI contexts belong to the retained `.circleci/config.yml`,
  not to `.github/workflows/pr-required.yml`.
- `bioetl-github-read-only` is restricted to the project and trusted main jobs.
- `bioetl-ghcr-publish` and `bioetl-security-events-write` separate registry and
  SARIF permissions. Their credential population and successful publication
  acceptance remain pending in #11931.
- Publication follows successful same-source gates and a separate approval.
  Failed, canceled, missing or stale evidence must block publication.

## Related

- Full table: [ci-workflow-map.md](ci-workflow-map.md)
- [github-setup-plan.md](../03-guides/github-setup-plan.md)
