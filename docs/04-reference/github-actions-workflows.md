______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-16'

______________________________________________________________________

# GitHub Actions Workflow Inventory

## Purpose

This page is the canonical published inventory of the **38** live GitHub Actions
workflows shipped under `.github/workflows/`.

Use it when you need to answer:

- which workflow file owns a given CI, nightly, release, or governance lane;
- whether a workflow is PR-facing, scheduled, or reusable-only;
- which workflows are active versus explicitly deprecated helper workflows.

## Source Of Truth

- Workflow files: `.github/workflows/*.yml`
- Governance policy: `docs/00-project/governance/05-github-policy.md`
- Syntax and policy guards: `tests/architecture/test_workflow_yaml_syntax.py`
  plus the workflow-specific architecture tests under `tests/architecture/`

## Classification

### PR / push verification workflows

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `chembl-baseline-smoke.yml` | `ChemblBaseline Smoke` | `push`, `pull_request`, `workflow_dispatch` | ChEMBL baseline smoke and reconciliation checks |
| `commit-lint.yml` | `Commit Lint` | `pull_request` | Conventional-commit policy gate |
| `compiled-artifacts-block.yml` | `Block Compiled Python Artifacts` | `push`, `pull_request` | Blocks checked-in `.pyc` and similar compiled artifacts |
| `consolidation-gates.yml` | `consolidation-gates` | `push`, `pull_request`, `workflow_dispatch` | Merge-campaign quality/architecture gate |
| `contract-governance-fast-check.yml` | `Contract Governance Fast Check` | `push`, `pull_request` | Fast contract-registry and schema governance checks |
| `docs.yml` | `Docs & Diagrams` | `push`, `pull_request` | Docs governance, MkDocs validation, Mermaid validation, diagram drift |
| `duplication-complexity.yml` | `Duplication and Complexity Checks` | `push`, `pull_request` | Duplication, constructor-args, and complexity gates |
| `e2e-matrix-health.yml` | `E2E Matrix Health` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | Blocking and nightly E2E matrix smoke lanes |
| `import-linter.yml` | `Lint and Architecture Gates` | `push`, `pull_request`, `workflow_dispatch` | Ruff/import-linter/architecture fast gates |
| `port-contracts.yml` | `Port Contract Tests` | `push`, `pull_request`, `workflow_dispatch` | Port-protocol and hypothesis contract tests |
| `provider-contract-drift.yml` | `Provider Contract Drift` | `push`, `pull_request`, `workflow_dispatch` | Provider contract replay/drift gate |
| `root-hygiene.yml` | `Root Hygiene` | `push`, `pull_request`, `workflow_dispatch` | Root-surface cleanliness and governance checks |
| `schema-governance.yml` | `Schema Governance` | `push`, `pull_request` | Generated artifacts, schema parity, schema drift |
| `security.yml` | `Security Scans` | `push`, `pull_request` | Secrets, dependency, and Bandit scans |
| `semantic-governance.yml` | `Semantic Pipeline Governance` | `push`, `pull_request` | Semantic pipeline contract/policy governance |
| `skills-consistency.yml` | `Skills Consistency` | `push`, `pull_request` | Local skill mirror consistency |
| `tests.yml` | `Tests` | `push`, `pull_request` | Main test matrix, DQ gates, coverage, telemetry, control-plane E2E |
| `type-checking.yml` | `Type Checking (Strict)` | `push`, `pull_request`, `workflow_dispatch` | Strict mypy lane |
| `validate-vendored-mermaid-assets.yml` | `Validate vendored Mermaid assets` | `push`, `pull_request` | Vendored Mermaid asset presence check |
| `coderabbit.yml` | `CodeRabbit` | `pull_request`, `push`, `workflow_dispatch` | CodeRabbit CLI automated code review |

### Scheduled / periodic workflows

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `architecture-docs-nightly.yml` | `Architecture Docs Nightly` | `schedule`, `workflow_dispatch` | Regenerates architecture dependency-doc artifacts |
| `architecture.yml` | `Architecture Metrics` | `schedule`, `workflow_dispatch` | Heavy architecture metrics and periodic boundary baselines |
| `contract-tests.yml` | `Monthly Contract Tests` | `schedule`, `workflow_dispatch` | Scheduled full contract-test lane |
| `diagram-nightly.yml` | `Diagram Nightly Regression` | `schedule`, `workflow_dispatch` | Diagram regression/nightly canary |
| `docs-kpi-weekly.yml` | `Docs KPI Weekly` | `schedule`, `workflow_dispatch` | Weekly docs KPI/reporting lane |
| `mutation-testing.yml` | `Mutation Testing` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | Mutation-testing lane with scheduled coverage |
| `nightly-replay-parity.yml` | `nightly-replay-parity` | `schedule`, `workflow_dispatch` | Replay/determinism parity validation |
| `performance-nightly.yml` | `Performance Nightly` | `schedule`, `workflow_dispatch` | Performance-regression gate |
| `pr-hygiene.yml` | `PR Hygiene` | `schedule`, `workflow_dispatch` | Stale report-noise draft PR cleanup under repository hygiene policy |
| `quality-debt-weekly.yml` | _(unnamed in YAML)_ | `schedule`, `workflow_dispatch` | Weekly quality-debt scorecard/report lane |
| `stale.yml` | `Stale` | `schedule` | Issue/PR staleness automation |
| `vacuum.yml` | `Weekly VACUUM` | `schedule`, `workflow_dispatch` | Scheduled Delta VACUUM maintenance |

### Release, packaging, and repository automation

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `dashboard-render-host.yml` | `Dashboard render release evidence (host-only)` | `workflow_dispatch` | Dashboard rendering and release evidence generation on self-hosted runner |
| `docker.yml` | `Docker Build & Compose Validation` | `push`, `pull_request` | Optional helper-image and compose validation |
| `labeler.yml` | `Labeler` | `pull_request_target` | Applies repository labels to PRs |
| `release.yml` | _(unnamed in YAML)_ | `release`, `workflow_dispatch` | Build, publish, and release-asset workflow |

### Reusable / compatibility-only helpers

| File | Workflow name | Triggers | Current status |
| --- | --- | --- | --- |
| `reusable-mermaid-setup.yml` | `[DEPRECATED] Reusable Mermaid setup` | `workflow_call` | Deprecated reusable helper |
| `reusable-setup.yml` | `[DEPRECATED] Reusable CI setup` | `workflow_call` | Deprecated reusable helper |

## Quick Routing

| Need | Start with |
| --- | --- |
| Main PR validation/test matrix | `tests.yml` |
| Docs, MkDocs, Mermaid, diagram drift | `docs.yml` |
| Schema and generated-artifact drift | `schema-governance.yml` |
| Security scans | `security.yml` |
| Nightly replay / determinism parity | `nightly-replay-parity.yml` |
| Stale report-noise draft PR cleanup | `pr-hygiene.yml` |
| Weekly debt governance | `quality-debt-weekly.yml` |
| Release build/publish flow | `release.yml` |

## Boundary Notes

- This inventory is descriptive; branch protection and required-check policy
  still live in the GitHub governance docs and repository settings.
- The reusable setup workflows are retained for compatibility but are explicitly
  marked deprecated in the workflow files themselves.
- If a workflow file is added, removed, renamed, or materially repurposed,
  update this page together with any workflow-specific governance docs.

## Related References

- [GitHub Local Workflow](../03-guides/github-local-workflow.md)
- [Project Navigator](../00-project/00-map.md)
- [Workflow Catalog](workflow-catalog.md)
