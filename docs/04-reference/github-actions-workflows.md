______________________________________________________________________

Version: 1.0.5
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-09'

______________________________________________________________________

# GitHub Actions Workflow Inventory

## Purpose

This page is the canonical published inventory of the **48** live GitHub Actions
workflows shipped under `.github/workflows/` on the default branch.
The count is derived from the tracked `*.yml` files; it is not a separately
maintained target and it is **not** equal to the GitHub Actions API
`total_count`. The API also returns dynamic hosted workflows (Dependabot,
CodeQL default setup, Copilot, Codex) and orphan temp files that are not in
this tree. Those extras are owned by [#10268](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10268)
(docs live-state) and [#10265](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10265)
(orphan temp). Do not treat them as canonical lanes here.

GitHub live `state` in the tables below is the Actions UI/API value
(`active` or `disabled_manually`) after the #10263 map. `deprecated` reusable
helpers stay `disabled_manually` and **MUST** remain so. Every canonical file
has a Decision of `active` or `keep-disabled`.

Use it when you need to answer:

- which workflow file owns a given CI, nightly, release, or governance lane;
- whether a workflow is PR-facing, scheduled, or reusable-only;
- whether the GitHub UI lane is live (`active`) or intentionally
  `keep-disabled`.

## Source Of Truth

- Workflow files: `.github/workflows/*.yml`
- Governance policy: `docs/00-project/governance/05-github-policy.md`
- Syntax and policy guards: `tests/architecture/test_workflow_yaml_syntax.py`
  plus the workflow-specific architecture tests under `tests/architecture/`
- Inventory parity guard:
  `tests/architecture/test_check_doc_links_guardrails.py::test_github_actions_workflow_inventory_matches_live_repo`
- Disabled-map guard: `tests/architecture/test_gha_disabled_map_10263.py`
- Focused local parity command:
  `python -m scripts.docs check-links --workflow-inventory`

## Classification

GitHub live state snapshot: GET `2026-09-09`, then `docs.yml` and
`compiled-artifacts-block.yml` re-enabled the same day as PR-gate reusable
owners (#10263). Do not re-enable other disabled canonical lanes without a
new spend/safety decision.

### PR / push verification workflows

| File | Workflow name | Triggers | GitHub live state | Decision | Primary purpose |
| --- | --- | --- | --- | --- | --- |
| `branch-hygiene.yml` | `Branch Hygiene` | `pull_request`, `schedule`, `workflow_dispatch` | `active` | `active` | Validates PR branch names and generates the periodic branch-cleanup inventory |
| `chembl-baseline-smoke.yml` | `ChemblBaseline Smoke` | `push`, `pull_request`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | ChEMBL baseline smoke and reconciliation checks |
| `commit-lint.yml` | `Commit Lint` | `workflow_call` | `active` | `active` | Conventional-commit policy gate |
| `compiled-artifacts-block.yml` | `Block Compiled Python Artifacts` | `workflow_call`, `push` | `active` | `active` | Blocks checked-in `.pyc` and similar compiled artifacts; re-enabled #10263 as `pr-required.yml` owner |
| `consolidation-gates.yml` | `consolidation-gates` | `workflow_dispatch` | `active` | `active` | Merge-campaign quality/architecture gate |
| `contract-governance-fast-check.yml` | `Contract Governance Fast Check` | `push`, `pull_request` | `disabled_manually` | `keep-disabled` | Fast contract-registry and schema governance checks |
| `dashboard-first-window-noscroll.yml` | `Dashboard first-window no-scroll` | `push`, `pull_request` | `active` | `active` | First-window no-scroll gate for all seven shipped dashboard UIDs (DASH-FIT-004) |
| `docs.yml` | `Docs & Diagrams` | `workflow_call`, `push` | `active` | `active` | Docs governance, MkDocs validation, Mermaid validation, diagram drift; re-enabled #10263 as `pr-required.yml` owner |
| `duplication-complexity.yml` | `Duplication and Complexity Checks` | `workflow_call`, `push` | `active` | `active` | Duplication, constructor-args, and complexity gates |
| `e2e-matrix-health.yml` | `E2E Matrix Health` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | `active` | `active` | Blocking and nightly E2E matrix smoke lanes |
| `import-linter.yml` | `Lint and Architecture Gates` | `workflow_call`, `push`, `workflow_dispatch` | `active` | `active` | Ruff/import-linter/architecture fast gates |
| `pr-required.yml` | `PR Gate Complete` | `pull_request`, `workflow_dispatch` | `active` | `active` | Always-materialized fail-closed coordinator for the canonical reusable owners |
| `port-contracts.yml` | `Port Contract Tests` | `push`, `pull_request`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Port-protocol and hypothesis contract tests |
| `provider-contract-drift.yml` | `Provider Contract Drift` | `push`, `pull_request`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Provider contract replay/drift gate |
| `root-hygiene.yml` | `Root Hygiene` | `workflow_call`, `push`, `workflow_dispatch` | `active` | `active` | Root-surface cleanliness and governance checks |
| `schema-governance.yml` | `Schema Governance` | `workflow_call`, `push` | `active` | `active` | Generated artifacts, schema parity, schema drift |
| `codeql.yml` | `CodeQL` | `workflow_call`, `push`, `schedule` | `active` | `active` | Advanced Python CodeQL SAST; default setup off |
| `dependency-review.yml` | `Dependency review` | `pull_request` | `active` | `active` | PR-time HIGH/CRITICAL dependency review on lockfile/manifest changes |
| `security.yml` | `Security Scans` | `workflow_call`, `push` | `active` | `active` | Secrets, pip-audit, Bandit, Gitleaks, OSV-Scanner |
| `zizmor.yml` | `zizmor` | `push`, `pull_request` | `active` | `active` | High-confidence GitHub Actions YAML audit |
| `semantic-governance.yml` | `Semantic Pipeline Governance` | `push`, `pull_request` | `disabled_manually` | `keep-disabled` | Semantic pipeline contract/policy governance |
| `skills-consistency.yml` | `Skills Consistency` | `push`, `pull_request`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Local skill mirrors plus Codex–Junie runtime parity |
| `tests.yml` | `Tests` | `workflow_call`, `push` | `active` | `active` | Main test matrix, DQ gates, coverage, telemetry, control-plane E2E |
| `type-checking.yml` | `Type Checking (Strict)` | `workflow_call`, `push`, `workflow_dispatch` | `active` | `active` | Strict mypy lane |
| `validate-vendored-mermaid-assets.yml` | `Validate vendored Mermaid assets` | `push`, `pull_request` | `disabled_manually` | `keep-disabled` | Vendored Mermaid asset presence check |
| `coderabbit.yml` | `CodeRabbit` | `push`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | CodeRabbit CLI automated code review |

### Scheduled / periodic workflows

| File | Workflow name | Triggers | GitHub live state | Decision | Primary purpose |
| --- | --- | --- | --- | --- | --- |
| `architecture-docs-nightly.yml` | `Architecture Docs Nightly` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Regenerates architecture dependency-doc artifacts |
| `architecture.yml` | `Architecture Metrics` | `schedule`, `workflow_dispatch` | `active` | `active` | Heavy architecture metrics and periodic boundary baselines |
| `contract-tests.yml` | `Monthly Contract Tests` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Scheduled full contract-test lane |
| `diagram-nightly.yml` | `Diagram Nightly Regression` | `schedule`, `workflow_dispatch` | `active` | `active` | Diagram regression/nightly canary |
| `docs-kpi-weekly.yml` | `Docs KPI Weekly` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Weekly docs KPI plus calendar runtime-mirror/freshness drift |
| `github-settings-quarterly-review.yml` | `Quarterly GitHub Settings Review` | `schedule`, `workflow_dispatch` | `active` | `active` | Read-only quarterly GitHub settings review |
| `memory-freshness.yml` | `Memory freshness` | `pull_request`, `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Repository memory freshness and contract checks |
| `memory-retention.yml` | `Memory Retention Policy` | `schedule`, `pull_request`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Weekly and change-triggered non-destructive episodic-memory retention policy check |
| `mutation-testing.yml` | `Mutation Testing` | `push`, `pull_request`, `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Mutation-testing lane with scheduled coverage |
| `nightly-replay-parity.yml` | `nightly-replay-parity` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Replay/determinism parity validation |
| `performance-nightly.yml` | `Performance Nightly` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Performance-regression gate |
| `pr-hygiene.yml` | `PR Hygiene` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Stale report-noise draft PR cleanup under repository hygiene policy |
| `quality-debt-weekly.yml` | `Quality Debt Weekly` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Weekly quality-debt scorecard/report lane |
| `scorecard.yml` | `OpenSSF Scorecard` | `schedule`, `workflow_dispatch`, `push` | `active` | `active` | Weekly non-blocking OpenSSF Scorecard baseline |
| `stale.yml` | `Stale` | `schedule` | `disabled_manually` | `keep-disabled` | Issue/PR staleness automation |
| `vacuum.yml` | `Weekly VACUUM` | `schedule`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Scheduled Delta VACUUM maintenance |

### Release, packaging, and repository automation

| File | Workflow name | Triggers | GitHub live state | Decision | Primary purpose |
| --- | --- | --- | --- | --- | --- |
| `dashboard-render-host.yml` | `Dashboard render release evidence (host-only)` | `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Dashboard rendering and release evidence generation on self-hosted runner |
| `docker.yml` | `Docker Build & Compose Validation` | `workflow_call`, `push`, `workflow_dispatch` | `active` | `active` | Optional helper-image and compose validation |
| `labeler.yml` | `Labeler` | `pull_request_target` | `disabled_manually` | `keep-disabled` | Applies repository labels to PRs |
| `release.yml` | `Release` | `release`, `workflow_dispatch` | `disabled_manually` | `keep-disabled` | Build, publish, and release-asset workflow |

### Reusable / compatibility-only helpers

| File | Workflow name | Triggers | GitHub live state | Decision | Current status |
| --- | --- | --- | --- | --- | --- |
| `reusable-mermaid-setup.yml` | `[DEPRECATED] Reusable Mermaid setup` | `workflow_call` | `disabled_manually` | `keep-disabled` | Deprecated reusable helper |
| `reusable-setup.yml` | `[DEPRECATED] Reusable CI setup` | `workflow_call` | `disabled_manually` | `keep-disabled` | Deprecated reusable helper |

## Keep-disabled reasons (#10263)

These lanes stay `disabled_manually` until a later measured decision. Do not
enable heavy nightlies without Actions spend evidence. Do not reopen #9975 or
#9979.

| File | Why keep-disabled |
| --- | --- |
| `architecture-docs-nightly.yml` | Optional nightly doc regen; overlap with `docs.yml` and `architecture.yml`; no spend measurement |
| `chembl-baseline-smoke.yml` | Optional smoke; not a `pr-required.yml` owner |
| `coderabbit.yml` | Third-party CLI review; extra Actions spend |
| `contract-governance-fast-check.yml` | Overlaps `schema-governance.yml`; not a `pr-required.yml` owner |
| `contract-tests.yml` | Monthly live-API lane; extra spend |
| `dashboard-render-host.yml` | Self-hosted dispatch-only; enable only when the observability host is required |
| `docs-kpi-weekly.yml` | Optional weekly KPI; do not change KPI thresholds to justify enable |
| `labeler.yml` | `pull_request_target`; re-enable only after live GitHub labels match `.github/labeler.yml` and `docs/00-project/governance/github-label-taxonomy.md` |
| `memory-freshness.yml` | Optional memory lane; not a `pr-required.yml` owner |
| `memory-retention.yml` | Optional memory lane; extra scheduled spend |
| `mutation-testing.yml` | Heavy weekly/PR mutation campaign; extra spend |
| `nightly-replay-parity.yml` | Heavy nightly replay; extra spend |
| `performance-nightly.yml` | Heavy nightly benchmarks; extra spend |
| `port-contracts.yml` | Supporting contracts lane; not invoked by `pr-required.yml` |
| `pr-hygiene.yml` | Depends on the `stale` label from `stale.yml`; keep both disabled together |
| `provider-contract-drift.yml` | Optional drift lane; not a `pr-required.yml` owner |
| `quality-debt-weekly.yml` | Optional weekly scorecard; do not raise debt budgets to justify enable |
| `release.yml` | Enable only for an actual release/publish event |
| `reusable-mermaid-setup.yml` | Deprecated; use `.github/actions/setup-mermaid` |
| `reusable-setup.yml` | Deprecated; use `.github/actions/setup-python-uv` |
| `semantic-governance.yml` | Overlaps schema/docs governance; not a `pr-required.yml` owner |
| `skills-consistency.yml` | Optional AI-runtime parity lane; not a `pr-required.yml` owner |
| `stale.yml` | YAML 14/7 PR stale/close contradicts `.github/PULL_REQUEST_HYGIENE.md` (21 days, draft + report-noise only). Do not enable until days/exemptions match that policy. Do not weaken stale to close non-draft engineering PRs. |
| `vacuum.yml` | Optional Delta VACUUM maintenance; extra spend |
| `validate-vendored-mermaid-assets.yml` | Covered by `docs.yml` Mermaid jobs when that owner is active |

## Quick Routing

Route only to **active** GitHub lanes. Keep-disabled files above do not run.

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
| PR branch naming and cleanup inventory | `branch-hygiene.yml` |
| Compiled artifact block | `compiled-artifacts-block.yml` |

## Boundary Notes

- This inventory is descriptive; branch protection and required-check policy
  still live in the GitHub governance docs and repository settings.
- The reusable setup workflows are retained for compatibility but are explicitly
  marked deprecated in the workflow files themselves and remain
  `keep-disabled`.
- YAML `on.schedule` on a `keep-disabled` workflow is a cadence claim only; it
  does **not** run while GitHub `state` is `disabled_manually`.
- If a workflow file is added, removed, renamed, or materially repurposed,
  update this page together with any workflow-specific governance docs. The
  focused parity command above must report neither missing nor extra workflow
  files.

## Self-hosted runner isolation (`dashboard-render-host.yml`)

Host-only Grafana render evidence runs on a dedicated self-hosted runner
label set: `[self-hosted, bioetl-observability]`. The workflow remains
`keep-disabled` (#10263) until an operator explicitly needs host render
evidence.

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

## Related References

- [GitHub Local Workflow](../03-guides/github-local-workflow.md)
- [Project Navigator](../00-project/00-map.md)
- [Workflow Catalog](workflow-catalog.md)
- [CI workflow map](../05-operations/ci-workflow-map.md)
