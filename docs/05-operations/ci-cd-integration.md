______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# CI/CD Pipeline Integration Guide

**Issue:** #6554
**SSOT map:** [ci-workflow-map.md](ci-workflow-map.md) (38 workflows)
**Also:** [github-local-workflow.md](../03-guides/github-local-workflow.md)

## Overview

CI is GitHub Actions under `.github/workflows/`. Local-Only product runtime does
**not** require cloud deploy for correctness; CI enforces quality gates.

## Major lanes

| Lane | Workflows (examples) | Purpose |
| --- | --- | --- |
| Tests | `tests.yml`, e2e matrix | Unit/integration |
| Architecture | `architecture.yml`, `import-linter.yml` | Layering, debt gates |
| Docs/diagrams | `docs.yml`, `diagram-nightly.yml` | MkDocs, mermaid, drift |
| Contracts | `contract-tests.yml`, schema/semantic governance | Contract SSOT |
| Security/quality | `security.yml`, duplication, type-checking | Hygiene |
| Release | `release.yml` | Packaging |

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

## Artifacts

- Test reports, coverage, diagram PNG artifacts (CI-only after DOC-GOV-02)
- Docs link-check JSON
- Do not commit `docs/site/` build output

## Secrets

- Use GitHub Actions secrets; never commit tokens
- `.env` files are machine-local and require explicit approval to edit

## Related

- Full table: [ci-workflow-map.md](ci-workflow-map.md)
- [github-setup-plan.md](../03-guides/github-setup-plan.md)
