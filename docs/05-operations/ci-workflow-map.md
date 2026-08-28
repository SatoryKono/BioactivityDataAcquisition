______________________________________________________________________

Version: 1.0.1
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-08-21'

______________________________________________________________________

# CI / GitHub Actions Workflow Map

Curated map of `.github/workflows/*` (DOC-GOV-06 / #6886).
**Count at verification:** 46 workflow files.
YAML self-description remains authoritative for triggers/secrets; this page is
the human index.

## How to use

1. Find the concern in the table.
2. Open the workflow file for `on:`, jobs, and required secrets.
3. Prefer existing reusable/local scripts over inventing parallel gates.

## Workflow catalog

| Workflow file | Display name | Purpose (summary) |
| --- | --- | --- |
| `architecture.yml` | Architecture Metrics | Architecture debt gates, scorecard, hotspots |
| `architecture-docs-nightly.yml` | Architecture Docs Nightly | Nightly architecture/doc sync checks |
| `branch-hygiene.yml` | Branch Hygiene | PR branch-name policy and periodic branch-cleanup inventory |
| `chembl-baseline-smoke.yml` | ChemblBaseline Smoke | ChEMBL baseline smoke lane |
| `coderabbit.yml` | CodeRabbit | Automated review integration |
| `codeql.yml` | CodeQL | Python CodeQL SAST to GitHub code scanning |
| `commit-lint.yml` | Commit Lint | Conventional commit message lint |
| `compiled-artifacts-block.yml` | Block Compiled Python Artifacts | Fail on committed bytecode/build junk |
| `consolidation-gates.yml` | consolidation-gates | Consolidation / cleanup governance gates |
| `contract-governance-fast-check.yml` | Contract Governance Fast Check | Fast contract surface check |
| `contract-tests.yml` | Monthly Contract Tests | Scheduled deep contract tests |
| `dashboard-first-window-noscroll.yml` | Dashboard first-window no-scroll | First-window no-scroll gate for all seven shipped dashboard UIDs (DASH-FIT-004) |
| `dashboard-render-host.yml` | Dashboard render release evidence | Host-only Grafana render evidence on self-hosted `[self-hosted, bioetl-observability]`; `workflow_dispatch` only — see isolation notes in `docs/04-reference/github-actions-workflows.md` |
| `dependency-review.yml` | Dependency review | PR-time HIGH/CRITICAL lockfile/manifest review |
| `diagram-nightly.yml` | Diagram Nightly Regression | Nightly diagram regression / PNG compat |
| `docker.yml` | Docker Build & Compose Validation | Optional Docker contract (ADR-010 adjunct), reproducible Trivy/SBOM baseline, blocking CRITICAL+HIGH+MEDIUM image gate, and no-rebuild promotion of the scanned image |
| `docs.yml` | Docs & Diagrams | MkDocs, links, mermaid lint, render, drift |
| `docs-kpi-weekly.yml` | Docs KPI Weekly | Documentation navigation KPI plus calendar freshness/runtime-mirror drift |
| `duplication-complexity.yml` | Duplication and Complexity Checks | Dup/complexity quality gates |
| `e2e-matrix-health.yml` | E2E Matrix Health | End-to-end matrix health |
| `import-linter.yml` | Lint and Architecture Gates | import-linter + layer architecture |
| `labeler.yml` | Labeler | PR auto-labeling |
| `memory-freshness.yml` | Memory freshness | Repository memory freshness and contract checks |
| `memory-retention.yml` | Memory Retention Policy | Weekly and change-triggered non-destructive episodic-memory retention policy check |
| `mutation-testing.yml` | Mutation Testing | Mutation testing campaign |
| `nightly-replay-parity.yml` | nightly-replay-parity | Replay/determinism parity |
| `performance-nightly.yml` | Performance Nightly | Performance benchmarks |
| `port-contracts.yml` | Port Contract Tests | Domain port contract tests |
| `pr-hygiene.yml` | PR Hygiene | PR hygiene checks |
| `provider-contract-drift.yml` | Provider Contract Drift | Provider contract drift detection |
| `quality-debt-weekly.yml` | Quality Debt Weekly | Debt budget / scorecard weekly |
| `release.yml` | Release | Release packaging/publish |
| `reusable-mermaid-setup.yml` | [DEPRECATED] Reusable Mermaid setup | Deprecated reusable workflow |
| `reusable-setup.yml` | [DEPRECATED] Reusable CI setup | Deprecated reusable workflow |
| `root-hygiene.yml` | Root Hygiene | Root allowlist / clutter gates |
| `schema-governance.yml` | Schema Governance | Schema governance checks |
| `scorecard.yml` | OpenSSF Scorecard | Weekly non-blocking OpenSSF Scorecard baseline |
| `security.yml` | Security Scans | Secrets, pip-audit, Bandit, Gitleaks, OSV-Scanner |
| `semantic-governance.yml` | Semantic Pipeline Governance | Semantic pipeline governance |
| `skills-consistency.yml` | Skills Consistency | AI skill parity plus Codex–Junie runtime parity |
| `stale.yml` | Stale | Stale issue/PR automation |
| `tests.yml` | Tests | Primary unit/integration test matrix |
| `type-checking.yml` | Type Checking (Strict) | basedpyright / type gates |
| `vacuum.yml` | Weekly VACUUM | Storage/VACUUM maintenance job |
| `zizmor.yml` | zizmor | High-confidence GitHub Actions YAML audit |
| `validate-vendored-mermaid-assets.yml` | Validate vendored Mermaid assets | Vendored mermaid asset integrity |

## Docs-critical path

For documentation PRs, start with **`docs.yml`**:

| Job (typical) | Role |
| --- | --- |
| docs-governance / validate-mkdocs | Strict MkDocs + excludes |
| validate-mermaid / render-diagrams | ADR-040 render |
| check-diagram-drift | Source vs SVG on diagram PRs |
| link checks | `scripts.docs check-links` |

See also: [05-github-policy.md](../00-project/governance/05-github-policy.md),
[docs-verification.md](../03-guides/docs-verification.md).

## Maintenance

When adding a workflow:

1. Add a row here in the same PR.
2. Prefer extending an existing gate over a new always-on workflow.
3. Mark deprecated reusables clearly; do not reference them from new jobs.
