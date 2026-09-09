______________________________________________________________________

Version: 1.0.5
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-10'

______________________________________________________________________

# GitHub Actions Workflow Inventory

## Purpose

This page is the canonical published inventory of the **48** live GitHub Actions
workflow files tracked under `.github/workflows/`. The count is derived from
those tracked `*.yml` files; it is not GitHub's `GET /actions/workflows`
`total_count` and it is not a separately maintained target.

Live GET `2026-09-10`: API `total_count` is **77**. Do not claim that 48 equals
every workflow object GitHub returns.

| Bucket | Count | Meaning |
| --- | --- | --- |
| Tracked `.github/workflows/*.yml` | 48 | Canonical inventory on `main`; this page |
| GitHub-hosted `dynamic/**` | 10 | Dependabot, CodeQL default, agent reviewers; not PR gates |
| GitHub-only orphan temp/codex IDs | 16 | Files left `main`; `disabled_manually` after #10265 |
| GitHub-only residual deleted files | 3 | Former tracked workflows; `disabled_manually`; not gates |
| API `total_count` | 77 | 48 + 10 + 16 + 3 |

Use it when you need to answer:

- which workflow file owns a given CI, nightly, release, or governance lane;
- whether a workflow is PR-facing, scheduled, or reusable-only;
- which workflows are active versus explicitly deprecated helper workflows.

## Source Of Truth

- Workflow files: `.github/workflows/*.yml`
- Governance policy: `docs/00-project/governance/05-github-policy.md`
- Syntax and policy guards: `tests/architecture/test_workflow_yaml_syntax.py`
  plus the workflow-specific architecture tests under `tests/architecture/`
- Inventory parity guard:
  `tests/architecture/test_check_doc_links_guardrails.py::test_github_actions_workflow_inventory_matches_live_repo`
- Focused local parity command:
  `python -m scripts.docs check-links --workflow-inventory`

## Classification

### PR / push verification workflows

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `branch-hygiene.yml` | `Branch Hygiene` | `pull_request`, `schedule`, `workflow_dispatch` | Validates PR branch names and generates the periodic branch-cleanup inventory |
| `chembl-baseline-smoke.yml` | `ChemblBaseline Smoke` | `push`, `pull_request`, `workflow_dispatch` | ChEMBL baseline smoke and reconciliation checks |
| `commit-lint.yml` | `Commit Lint` | `workflow_call` | Conventional-commit policy gate |
| `compiled-artifacts-block.yml` | `Block Compiled Python Artifacts` | `workflow_call`, `push` | Blocks checked-in `.pyc` and similar compiled artifacts |
| `consolidation-gates.yml` | `consolidation-gates` | `workflow_dispatch` | Merge-campaign quality/architecture gate |
| `contract-governance-fast-check.yml` | `Contract Governance Fast Check` | `push`, `pull_request` | Fast contract-registry and schema governance checks |
| `dashboard-first-window-noscroll.yml` | `Dashboard first-window no-scroll` | `push`, `pull_request` | First-window no-scroll gate for all seven shipped dashboard UIDs (DASH-FIT-004) |
| `docs.yml` | `Docs & Diagrams` | `workflow_call`, `push` | Docs governance, MkDocs validation, Mermaid validation, diagram drift |
| `duplication-complexity.yml` | `Duplication and Complexity Checks` | `workflow_call`, `push` | Duplication, constructor-args, and complexity gates |
| `e2e-matrix-health.yml` | `E2E Matrix Health` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | Blocking and nightly E2E matrix smoke lanes |
| `import-linter.yml` | `Lint and Architecture Gates` | `workflow_call`, `push`, `workflow_dispatch` | Ruff/import-linter/architecture fast gates |
| `pr-required.yml` | `PR Gate Complete` | `pull_request`, `workflow_dispatch` | Always-materialized fail-closed coordinator for the canonical reusable owners |
| `port-contracts.yml` | `Port Contract Tests` | `push`, `pull_request`, `workflow_dispatch` | Port-protocol and hypothesis contract tests |
| `provider-contract-drift.yml` | `Provider Contract Drift` | `push`, `pull_request`, `workflow_dispatch` | Provider contract replay/drift gate |
| `root-hygiene.yml` | `Root Hygiene` | `workflow_call`, `push`, `workflow_dispatch` | Root-surface cleanliness and governance checks |
| `schema-governance.yml` | `Schema Governance` | `workflow_call`, `push` | Generated artifacts, schema parity, schema drift |
| `codeql.yml` | `CodeQL` | `workflow_call`, `push`, `schedule` | Advanced Python CodeQL SAST; default setup off |
| `dependency-review.yml` | `Dependency review` | `pull_request` | PR-time HIGH/CRITICAL dependency review on lockfile/manifest changes |
| `security.yml` | `Security Scans` | `workflow_call`, `push` | Secrets, pip-audit, Bandit, Gitleaks, OSV-Scanner |
| `zizmor.yml` | `zizmor` | `push`, `pull_request` | High-confidence GitHub Actions YAML audit |
| `semantic-governance.yml` | `Semantic Pipeline Governance` | `push`, `pull_request` | Semantic pipeline contract/policy governance |
| `skills-consistency.yml` | `Skills Consistency` | `push`, `pull_request`, `workflow_dispatch` | Local skill mirrors plus Codex–Junie runtime parity |
| `tests.yml` | `Tests` | `workflow_call`, `push` | Main test matrix, DQ gates, coverage, telemetry, control-plane E2E |
| `type-checking.yml` | `Type Checking (Strict)` | `workflow_call`, `push`, `workflow_dispatch` | Strict mypy lane |
| `validate-vendored-mermaid-assets.yml` | `Validate vendored Mermaid assets` | `push`, `pull_request` | Vendored Mermaid asset presence check |
| `coderabbit.yml` | `CodeRabbit` | `push`, `workflow_dispatch` | CodeRabbit CLI automated code review |

### Scheduled / periodic workflows

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `architecture-docs-nightly.yml` | `Architecture Docs Nightly` | `schedule`, `workflow_dispatch` | Regenerates architecture dependency-doc artifacts |
| `architecture.yml` | `Architecture Metrics` | `schedule`, `workflow_dispatch` | Heavy architecture metrics and periodic boundary baselines |
| `contract-tests.yml` | `Monthly Contract Tests` | `schedule`, `workflow_dispatch` | Scheduled full contract-test lane |
| `diagram-nightly.yml` | `Diagram Nightly Regression` | `schedule`, `workflow_dispatch` | Diagram regression/nightly canary |
| `docs-kpi-weekly.yml` | `Docs KPI Weekly` | `schedule`, `workflow_dispatch` | Weekly docs KPI plus calendar runtime-mirror/freshness drift |
| `github-settings-quarterly-review.yml` | `Quarterly GitHub Settings Review` | `schedule`, `workflow_dispatch` | Read-only quarterly GitHub settings review |
| `memory-freshness.yml` | `Memory freshness` | `pull_request`, `schedule`, `workflow_dispatch` | Repository memory freshness and contract checks |
| `memory-retention.yml` | `Memory Retention Policy` | `schedule`, `pull_request`, `workflow_dispatch` | Weekly and change-triggered non-destructive episodic-memory retention policy check |
| `mutation-testing.yml` | `Mutation Testing` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | Mutation-testing lane with scheduled coverage |
| `nightly-replay-parity.yml` | `nightly-replay-parity` | `schedule`, `workflow_dispatch` | Replay/determinism parity validation |
| `performance-nightly.yml` | `Performance Nightly` | `schedule`, `workflow_dispatch` | Performance-regression gate |
| `pr-hygiene.yml` | `PR Hygiene` | `schedule`, `workflow_dispatch` | Stale report-noise draft PR cleanup under repository hygiene policy |
| `quality-debt-weekly.yml` | `Quality Debt Weekly` | `schedule`, `workflow_dispatch` | Weekly quality-debt scorecard/report lane |
| `scorecard.yml` | `OpenSSF Scorecard` | `schedule`, `workflow_dispatch`, `push` | Weekly non-blocking OpenSSF Scorecard baseline |
| `stale.yml` | `Stale` | `schedule` | Issue/PR staleness automation |
| `vacuum.yml` | `Weekly VACUUM` | `schedule`, `workflow_dispatch` | Scheduled Delta VACUUM maintenance |

### Release, packaging, and repository automation

| File | Workflow name | Triggers | Primary purpose |
| --- | --- | --- | --- |
| `dashboard-render-host.yml` | `Dashboard render release evidence (host-only)` | `workflow_dispatch` | Dashboard rendering and release evidence generation on self-hosted runner |
| `docker.yml` | `Docker Build & Compose Validation` | `workflow_call`, `push`, `workflow_dispatch` | Optional helper-image and compose validation |
| `labeler.yml` | `Labeler` | `pull_request_target` | Applies repository labels to PRs |
| `release.yml` | `Release` | `release`, `workflow_dispatch` | Build, publish, and release-asset workflow |

### Reusable / compatibility-only helpers

| File | Workflow name | Triggers | Current status |
| --- | --- | --- | --- |
| `reusable-mermaid-setup.yml` | `[DEPRECATED] Reusable Mermaid setup` | `workflow_call` | Deprecated reusable helper |
| `reusable-setup.yml` | `[DEPRECATED] Reusable CI setup` | `workflow_call` | Deprecated reusable helper |

## Quick Routing

| Need | Start with |
| --- | --- |
| Main PR required-check coordinator | `pr-required.yml` |
| Test matrix owner | `tests.yml` |
| Docs, MkDocs, Mermaid, diagram drift | `docs.yml` |
| Dashboard first-window no-scroll (DASH-FIT-004) | `dashboard-first-window-noscroll.yml` |
| Schema and generated-artifact drift | `schema-governance.yml` |
| Security scans | `security.yml` |
| Dependency review | `dependency-review.yml` |
| CodeQL Python SAST | `codeql.yml` |
| OpenSSF Scorecard | `scorecard.yml` |
| zizmor Actions audit | `zizmor.yml` |
| Nightly replay / determinism parity | `nightly-replay-parity.yml` |
| Episodic-memory retention policy | `memory-retention.yml` |
| PR branch naming and cleanup inventory | `branch-hygiene.yml` |
| Stale report-noise draft PR cleanup | `pr-hygiene.yml` |
| Weekly debt governance | `quality-debt-weekly.yml` |
| Release build/publish flow | `release.yml` |

## Boundary Notes

- This inventory is descriptive; branch protection and required-check policy
  still live in the GitHub governance docs and repository settings.
- The reusable setup workflows are retained for compatibility but are explicitly
  marked deprecated in the workflow files themselves.
- If a workflow file is added, removed, renamed, or materially repurposed,
  update this page together with any workflow-specific governance docs. The
  focused parity command above must report neither missing nor extra workflow
  files.

## Self-hosted runner isolation (`dashboard-render-host.yml`)

Host-only Grafana render evidence runs on a dedicated self-hosted runner
label set: `[self-hosted, bioetl-observability]`.

| Control | Requirement |
| --- | --- |
| Trigger | **`workflow_dispatch` only** — never add `pull_request` / `pull_request_target` |
| Permissions | Workflow `contents: read` only |
| Secrets | `GRAFANA_USERNAME` / `GRAFANA_PASSWORD` injected only into the host job env |
| Code | Checkout of the **selected ref** at dispatch time (trusted operators) |
| Host | Runner must be isolated from general CI (dedicated host/VM, no shared untrusted PR jobs) |
| Dispatch ACL | Restrict who may run workflow_dispatch via GitHub org/repo roles |
| Residual risk | Host compromise can expose Grafana credentials; prefer short-lived tokens when available |

Do **not** expand this workflow to untrusted PR code paths. Operator checklist:
`docs/05-operations/runbooks/observability-checklist.md` (ownership
`@bioetl-observability`).

## GitHub-only orphan/disabled IDs

These workflow objects exist only on GitHub. They are not tracked under
`.github/workflows/` and are not canonical PR gates. After the files left
`main`, the objects stayed `active` and could still run from old SHAs. On
`2026-09-09` they were set to `disabled_manually`. Do not DELETE them from
this inventory, and do not re-enable them as required checks.

| Path | ID | State |
| --- | --- | --- |
| `.github/workflows/codex-baseline-diagnostic.yml` | 348464441 | `disabled_manually` |
| `.github/workflows/codex-ci-diagnostic.yml` | 348449565 | `disabled_manually` |
| `.github/workflows/codex-inventory-diagnostic.yml` | 348472435 | `disabled_manually` |
| `.github/workflows/codex-temp-coverage-inventory-diff.yml` | 349060658 | `disabled_manually` |
| `.github/workflows/codex-test-governance-refresh.yml` | 348870616 | `disabled_manually` |
| `.github/workflows/temp-trivy-artifact-diagnosis.yml` | 349397659 | `disabled_manually` |
| `.github/workflows/temporary-governance-artifact-9977.yml` | 349312647 | `disabled_manually` |
| `.github/workflows/temporary-governance-log-9977.yml` | 349328204 | `disabled_manually` |
| `.github/workflows/temporary-pr-10037-telemetry-refresh.yml` | 349405434 | `disabled_manually` |
| `.github/workflows/tmp-canonical-governance.yml` | 346434904 | `disabled_manually` |
| `.github/workflows/tmp-canonical-refresh.yml` | 346403953 | `disabled_manually` |
| `.github/workflows/tmp-canonical-test-governance.yml` | 346429358 | `disabled_manually` |
| `.github/workflows/tmp-final-pr9889-remote-baseline.yml` | 346596417 | `disabled_manually` |
| `.github/workflows/tmp-pr-9880-ci-repair.yml` | 346467453 | `disabled_manually` |
| `.github/workflows/tmp-pr-9889-final-governance.yml` | 346590707 | `disabled_manually` |
| `.github/workflows/tmp-remote-main-baseline-hashes.yml` | 349108333 | `disabled_manually` |

## GitHub-only residual deleted files

These objects still exist on GitHub after the YAML left `.github/workflows/`.
They are `disabled_manually` and MUST NOT be treated as canonical PR gates.

| Path | ID | State |
| --- | --- | --- |
| `.github/workflows/contract-snapshot-diff.yml` | 235363915 | `disabled_manually` |
| `.github/workflows/diagrams.yml` | 239669677 | `disabled_manually` |
| `.github/workflows/schema-drift-check.yml` | 235364479 | `disabled_manually` |

## GitHub-hosted dynamic workflows

Hosted `dynamic/**` objects count toward API `total_count`. They are not tracked
YAML and are not repository required-check owners.

| Path | ID | State |
| --- | --- | --- |
| `dynamic/agents/anthropic-code-agent` | 243971367 | `active` |
| `dynamic/agents/copilot-pull-request-reviewer` | 312611708 | `active` |
| `dynamic/agents/openai-code-agent` | 262875535 | `active` |
| `dynamic/anthropic-code-agent/claude` | 235054673 | `active` |
| `dynamic/copilot-pull-request-reviewer/copilot-pull-request-reviewer` | 215108871 | `active` |
| `dynamic/copilot-swe-agent/copilot` | 215109867 | `active` |
| `dynamic/dependabot/dependabot-updates` | 234158378 | `active` |
| `dynamic/dependabot/update-graph` | 344512696 | `active` |
| `dynamic/github-code-scanning/codeql` | 235193651 | `active` |
| `dynamic/openai-code-agent/codex` | 235140883 | `active` |

## Related References

- [GitHub Local Workflow](../03-guides/github-local-workflow.md)
- [Project Navigator](../00-project/00-map.md)
- [Workflow Catalog](workflow-catalog.md)
