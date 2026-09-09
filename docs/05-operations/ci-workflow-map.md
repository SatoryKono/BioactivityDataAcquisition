______________________________________________________________________

Version: 1.0.2
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-10'

______________________________________________________________________

# CI / GitHub Actions Workflow Map

Curated map of canonical `.github/workflows/*` (DOC-GOV-06 / #6886 / #10263).
**Count at verification:** 48 tracked workflow files on the default branch
(23 GitHub-`active`, 25 `keep-disabled`). That 48 is **not** GitHub API
`total_count` (live GET `2026-09-10`: **77** = tracked + `dynamic/**` + orphan
temp/residual). YAML self-description remains authoritative for
triggers/secrets; GitHub UI `state` is authoritative for whether the lane
actually runs. This page routes operators only to **active** lanes.

`pr-required.yml` (`pr-gate-complete`) is the repo-side coordinator. It is
**not** a GitHub ruleset required context while `main` (13643213) and
`root-hygiene-required-check` (15730586) stay `enforcement: disabled`
([#10267](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10267)).
Orphan temp / dynamic hosted workflows are out of scope here (#10265, #10268).

## How to use

1. Find the concern in the **active** table.
2. Open the workflow file for `on:`, jobs, and required secrets.
3. Prefer existing reusable/local scripts over inventing parallel gates.
4. Do not dispatch or wait on a `keep-disabled` lane; it does not run.

## Active workflow catalog

| Workflow file | Display name | Purpose (summary) |
| --- | --- | --- |
| `architecture.yml` | Architecture Metrics | Architecture debt gates, scorecard, hotspots |
| `branch-hygiene.yml` | Branch Hygiene | PR branch-name policy and periodic branch-cleanup inventory |
| `codeql.yml` | CodeQL | Advanced Python CodeQL SAST to GitHub code scanning; default setup stays off |
| `commit-lint.yml` | Commit Lint | Conventional commit message lint |
| `compiled-artifacts-block.yml` | Block Compiled Python Artifacts | Fail on committed bytecode/build junk; `pr-required.yml` owner (re-enabled #10263) |
| `consolidation-gates.yml` | consolidation-gates | Consolidation / cleanup governance gates |
| `dashboard-first-window-noscroll.yml` | Dashboard first-window no-scroll | First-window no-scroll gate for all seven shipped dashboard UIDs (DASH-FIT-004) |
| `dependency-review.yml` | Dependency review | PR-time HIGH/CRITICAL lockfile/manifest review |
| `diagram-nightly.yml` | Diagram Nightly Regression | Mermaid canary; full-corpus render/regression job disabled |
| `docker.yml` | Docker Build & Compose Validation | Optional Docker contract (ADR-010 adjunct), reproducible Trivy/SBOM baseline, blocking CRITICAL+HIGH+MEDIUM image gate, and no-rebuild promotion of the scanned image |
| `docs.yml` | Docs & Diagrams | MkDocs, links, Mermaid lint, targeted ChEMBL render, drift; `pr-required.yml` owner (re-enabled #10263) |
| `duplication-complexity.yml` | Duplication and Complexity Checks | Dup/complexity quality gates |
| `e2e-matrix-health.yml` | E2E Matrix Health | End-to-end matrix health |
| `github-settings-quarterly-review.yml` | Quarterly GitHub Settings Review | Read-only quarterly GitHub settings review |
| `import-linter.yml` | Lint and Architecture Gates | import-linter + layer architecture |
| `pr-required.yml` | PR Gate Complete | Fail-closed coordinator `pr-gate-complete`; not GitHub-required while rulesets are disabled (#10267) |
| `root-hygiene.yml` | Root Hygiene | Root allowlist / clutter gates |
| `schema-governance.yml` | Schema Governance | Schema governance checks |
| `scorecard.yml` | OpenSSF Scorecard | Weekly non-blocking OpenSSF Scorecard baseline |
| `security.yml` | Security Scans | Secrets, pip-audit, Bandit, Gitleaks, OSV-Scanner |
| `tests.yml` | Tests | Primary unit/integration test matrix |
| `type-checking.yml` | Type Checking (Strict) | basedpyright / type gates |
| `zizmor.yml` | zizmor | High-confidence GitHub Actions YAML audit |

## Keep-disabled catalog (#10263)

These files exist in git but GitHub `state` is `disabled_manually`. They are
not operator routing targets. Reasons live in
[github-actions-workflows.md](../04-reference/github-actions-workflows.md).

| Workflow file | Display name | Decision |
| --- | --- | --- |
| `architecture-docs-nightly.yml` | Architecture Docs Nightly | `keep-disabled` |
| `chembl-baseline-smoke.yml` | ChemblBaseline Smoke | `keep-disabled` |
| `coderabbit.yml` | CodeRabbit | `keep-disabled` |
| `contract-governance-fast-check.yml` | Contract Governance Fast Check | `keep-disabled` |
| `contract-tests.yml` | Monthly Contract Tests | `keep-disabled` |
| `dashboard-render-host.yml` | Dashboard render release evidence | `keep-disabled` |
| `docs-kpi-weekly.yml` | Docs KPI Weekly | `keep-disabled` |
| `labeler.yml` | Labeler | `keep-disabled` |
| `memory-freshness.yml` | Memory freshness | `keep-disabled` |
| `memory-retention.yml` | Memory Retention Policy | `keep-disabled` |
| `mutation-testing.yml` | Mutation Testing | `keep-disabled` |
| `nightly-replay-parity.yml` | nightly-replay-parity | `keep-disabled` |
| `performance-nightly.yml` | Performance Nightly | `keep-disabled` |
| `port-contracts.yml` | Port Contract Tests | `keep-disabled` |
| `pr-hygiene.yml` | PR Hygiene | `keep-disabled` |
| `provider-contract-drift.yml` | Provider Contract Drift | `keep-disabled` |
| `quality-debt-weekly.yml` | Quality Debt Weekly | `keep-disabled` |
| `release.yml` | Release | `keep-disabled` |
| `reusable-mermaid-setup.yml` | [DEPRECATED] Reusable Mermaid setup | `keep-disabled` |
| `reusable-setup.yml` | [DEPRECATED] Reusable CI setup | `keep-disabled` |
| `semantic-governance.yml` | Semantic Pipeline Governance | `keep-disabled` |
| `skills-consistency.yml` | Skills Consistency | `keep-disabled` |
| `stale.yml` | Stale | `keep-disabled` |
| `vacuum.yml` | Weekly VACUUM | `keep-disabled` |
| `validate-vendored-mermaid-assets.yml` | Validate vendored Mermaid assets | `keep-disabled` |

## Docs-critical path

For documentation PRs, start with **`docs.yml`** (GitHub-`active` after #10263):

| Job (typical) | Role |
| --- | --- |
| docs-governance / validate-mkdocs | Strict MkDocs + excludes |
| validate-mermaid | ADR-040 Mermaid syntax and changed-source lint |
| check-diagram-drift | Source vs SVG on diagram PRs |
| link checks | `scripts.docs check-links` |

See also: [05-github-policy.md](../00-project/governance/05-github-policy.md),
[docs-verification.md](../03-guides/docs-verification.md),
[github-actions-workflows.md](../04-reference/github-actions-workflows.md).

## Maintenance

When adding a workflow:

1. Add a row here in the same PR (active vs keep-disabled).
2. Prefer extending an existing gate over a new always-on workflow.
3. Mark deprecated reusables clearly; do not reference them from new jobs.
4. Record GitHub live `state` and a keep-disabled or active decision in the
   canonical inventory.
