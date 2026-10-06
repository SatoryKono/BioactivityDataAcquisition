______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-10-06'

______________________________________________________________________

# CI/CD Pipeline Integration Guide

**Issue:** #6554
**SSOT map:** [ci-workflow-map.md](ci-workflow-map.md) (52 legacy workflows and their replacement status)
**Also:** [github-local-workflow.md](../03-guides/github-local-workflow.md)

## Overview

CI runs through `.circleci/config.yml`. GitHub Actions are disabled; the retained
`.github/workflows/` files describe legacy behavior until the verified migration
cutover in #11930. Local-Only product runtime does not require cloud deployment.

For pull requests, select `ci-lane=pr-gate` (the default). Active main rulesets
require `ci/circleci: pr-gate-complete` and `ci/circleci: root-hygiene` on the
current source SHA, with strict freshness and no bypass. A successful maintenance
lane or an approval does not substitute for those checks. CodeQL is excluded
from required checks by the owner decision in #11929.

## Major lanes

| Lane | CircleCI jobs or typed ci-lane | Purpose |
| --- | --- | --- |
| Required PR gate | `classify`, `test-fast`, `test-integration`, `pr-gate-complete` | Catalog-driven checks and aggregate result |
| Architecture | `lint-arch`, `arch-tests`, `architecture-docs` | Layering, debt and generated documentation |
| Docs | `docs-governance`, `docs-kpi`, `skills-consistency` | Documentation and runtime mirror validation |
| Contracts | `dq-consistency`, `schema-governance`, `semantic-governance`, `port-contracts`, `provider-contract-drift` | Data and adapter contracts |
| Security/quality | `security-scans`, `mypy`, `duplication`, `root-hygiene` | Security and code quality gates |
| Docker | `docker-baseline`, `docker-publish` | Build and full baseline before separate publication approval |
| Release preparation | `release-validation` | Prepared wheel/sdist, install, tests, security and SPDX; remote acceptance and protected promotion pending |

Scheduled and manual lanes use typed pipeline parameters on main. The workflow
map records actual run IDs, schedule registration, input acceptance, disabled
surfaces and unresolved parity. Do not treat a configured lane as accepted until
its required artifacts and terminal result have been verified.

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

The README CI badge links to the main pipeline list; it identifies the provider,
not the result of a specific gate. The coverage badge states the 85% policy.
Use the exact source SHA, required GitHub statuses and linked CircleCI run for
acceptance. A project-wide badge can reflect a maintenance workflow and must not
be used as proof that the required PR gate passed.

## Artifacts

- Test reports, coverage, diagram PNG artifacts (CI-only after DOC-GOV-02)
- Docs link-check JSON
- Do not commit `docs/site/` build output

## Secrets

- Use restricted CircleCI contexts; never commit tokens.
- `bioetl-github-read-only` is restricted to the project and trusted main jobs.
- `bioetl-ghcr-publish` and `bioetl-security-events-write` separate registry and
  SARIF permissions. Their credential population and successful publication
  acceptance remain pending in #11931.
- Publication follows successful same-source gates and a separate approval.
  Failed, canceled, missing or stale evidence must block publication.
- `.env` files are machine-local and require explicit approval to edit

## Related

- Full table: [ci-workflow-map.md](ci-workflow-map.md)
- [github-setup-plan.md](../03-guides/github-setup-plan.md)
