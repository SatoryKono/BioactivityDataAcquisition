______________________________________________________________________

Version: 1.0.3
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

`pr-required.yml` (`pr-gate-complete`) is the repo-side coordinator **and**
the GitHub ruleset required context on `main` (ruleset `13643213`,
`enforcement: active` as of `2026-09-10T02:53:01+03:00`,
[#10267](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10267)).
Companion `root-hygiene-required-check` (15730586) stays `enforcement: disabled`.
Orphan temp / dynamic hosted workflows are out of scope here (#10265, #10268).

## CircleCI migration preparation (#11929 / #11931)

The map above records the legacy Actions inventory; it is not evidence that
Actions are running. Actions are disabled and billing restoration is out of scope.
CodeQL is excluded from required checks; optional analysis and workflow retirement
remain separate decisions. The CircleCI default-branch matrix reads the canonical
required-check catalog instead of maintaining a second gate list.

The isolated preparation branch adds a `ci-lane` pipeline parameter with default
`pr-gate`. Setting `ci-lane=docs-kpi` selects only the Docs KPI workflow on `main`;
it does not start the PR gate, mutation testing or Docker publication. The job
preserves the existing KPI limits (target 120, hard limit 135, zero orphans),
freshness validation and report artifacts. Run it through a CircleCI pipeline
trigger after the config is integrated; `type: approval` is not a trigger.
Other prepared opt-in lanes are `memory-retention` (check-only), `port-contracts`
(property checks enabled by default through `include-hypothesis`),
`skills-consistency` (verify-only, no approved runtime sync), and
`github-settings-review` (requires the restricted `bioetl-github-read-only`
context). All are main-only and isolated from the normal PR workflow. Context
registration, trigger activation, remaining event parity and external acceptance
are pending; these additions do not establish full legacy-workflow parity.
The prepared `performance` lane preserves benchmark budgets and the five-sample
window, emits JUnit/observations/JSON/Markdown artifacts, and fails on missing,
empty or over-budget evidence. It is opt-in and main-only; no benchmark run or
external nightly schedule is claimed.
The prepared `replay-parity` lane retains the determinism, idempotency, composite
resume and independent determinism recheck, with nonempty checksum comparison
and replay artifacts. `memory-freshness` checks and publishes evidence without
GitHub write credentials; its schedule-failure notification and PR event parity
remain pending. Both lanes are opt-in and main-only.

The prepared `mutation` lane additionally requires `pipeline.trigger.type=schedule`;
manual/API/PR triggers cannot start its four jobs. It preserves the existing four
targets and 70/60/60/60 score thresholds, fails on missing, empty or invalid stats,
and retains reports. No mutation execution or external schedule is claimed.

The intended weekly cadence is Monday 04:30 UTC. No external schedule has been
registered by this preparation change, and no successful remote run is claimed.

Independent phase-3 jobs may be prepared in parallel with phase A. Publishing
requires successful build/security/baseline gates and separate approval. Final
badges require the verified phase-B contract. Do not integrate this preparation
into the active coverage acceptance branch or run heavy jobs alongside its producer.

The prepared acceptance fixes use the architecture marker expression `not slow and
not benchmark and not memory`; pytest exit 5 remains a failure. Matrix workers
are capped at two, and the complete duplication scan uses a medium runner with
a 3072 MiB Node heap. Existing quality thresholds and scan paths are preserved.

## Migration disposition ledger (#11930 / #11931)

Current source inventory contains 52 workflows. Every row records the intended
replacement or retained local/disabled policy; "prepared" is not external acceptance.
No pending replacement authorizes deleting its source workflow. Scheduled entries
are UTC cron expressions from the source definitions, not registered CircleCI triggers.

| Source workflow | UTC schedule | Successor / disposition | Remaining acceptance |
| --- | --- | --- | --- |
| `architecture-docs-nightly.yml` | `15 2 * * *` | Architecture/docs audit lane | Pending port; preserve full audits and artifacts |
| `architecture.yml` | `20 2 * * *` | Architecture metrics lane | Pending port; canonical reporters and no budget growth |
| `branch-hygiene.yml` | `15 3 * * 1` | GitHub API branch/PR maintenance | Pending port; read-only inventory and trusted write boundary |
| `chembl-baseline-smoke.yml` | — | Representative offline smoke lane | Pending port; preserve cassette playback |
| `codeql.yml` | `17 4 * * 1` | Retire Actions definition at #11930 cutover | Not required; optional analysis lifecycle remains explicit |
| `coderabbit.yml` | — | Local CodeRabbit launcher | Retain local; external integration/event policy pending |
| `commit-lint.yml` | — | CircleCI commit-lint | Prepared required gate; external parity pending |
| `compiled-artifacts-block.yml` | — | CircleCI compiled-artifacts | Prepared required gate; external parity pending |
| `consolidation-gates.yml` | — | Manual consolidation lane | Pending port; inputs and artifacts must be preserved |
| `contract-governance-fast-check.yml` | — | Contract confidence lane | Pending port; not replaced by schema check alone |
| `contract-tests.yml` | — | Local live-provider contract runner | Retain local-only policy #11190; preserve inputs and failure evidence |
| `dashboard-first-window-noscroll.yml` | — | Dashboard host acceptance | Retain host dependency; pending automation boundary |
| `dashboard-render-host.yml` | — | Local render host runner | Retain local host; Grafana/render secrets never on ordinary PR |
| `dependency-review.yml` | — | Dependency diff security review | Pending replacement; do not drop HIGH/CRITICAL diff coverage |
| `diagram-nightly.yml` | — | Diagram lint plus local full render | Keep disabled full-render surface; port only active checks |
| `docker.yml` | — | CircleCI docker-build plus protected promotion | Build prepared; Trivy/baseline/digest promotion pending |
| `docs-kpi-weekly.yml` | `30 4 * * 1` | CircleCI docs-kpi | Prepared opt-in lane; external schedule pending |
| `docs.yml` | — | CircleCI docs-governance | Prepared required gate; full docs/render parity pending |
| `duplication-complexity.yml` | — | CircleCI duplication | Prepared required gate; full scan thresholds preserved |
| `e2e-matrix-health.yml` | `30 2 * * *` | E2E replay and controlled live lanes | Pending port; preserve reruns, skip SLO and credential separation |
| `github-settings-quarterly-review.yml` | `23 6 1 1,4,7,10 *` | CircleCI github-settings-review | Prepared opt-in lane; restricted context and schedule pending |
| `import-linter.yml` | — | CircleCI lint-arch and arch-tests | Prepared gates; full external architecture acceptance pending |
| `labeler.yml` | — | GitHub API label maintenance | Pending port; trusted actor and scoped issue/PR write access |
| `memory-freshness.yml` | `17 5 * * 1` | CircleCI memory-freshness | Prepared check-only lane; PR parity and scheduled failure notification pending |
| `memory-retention.yml` | `17 4 * * 1` | CircleCI memory-retention | Prepared check-only lane; triggers pending, no prune mutation |
| `mutation-testing.yml` | `0 0 * * 0` | Scheduled-only mutation lane | Prepared; compiler, schedule and four-target execution acceptance pending; 70/60/60/60 thresholds unchanged |
| `nightly-replay-parity.yml` | `30 2 * * *` | CircleCI replay-parity | Prepared four-run checksum lane; remote parity and schedule pending |
| `no-partial-tree-commits.yml` | — | Full-tree guard in root governance | Local guard verified; CircleCI integration required before cutover |
| `opencode-pr-review.yml` | — | Retain disabled review stub policy | Do not activate unpinned installer or write paths |
| `opencode-triage.yml` | — | Retain disabled triage stub policy | Do not activate unpinned installer or write paths |
| `performance-nightly.yml` | `0 3 * * *` | CircleCI performance | Prepared opt-in lane; remote benchmark evidence and schedule pending |
| `port-contracts.yml` | — | CircleCI port-contracts | Prepared Hypothesis-enabled lane; push/PR event parity pending |
| `pr-hygiene.yml` | — | GitHub API PR maintenance | Pending port; validation and trusted write boundary |
| `pr-required.yml` | — | CircleCI classify/pr-gate-complete | Prepared catalogue-backed contract; main acceptance/rulesets pending |
| `provider-contract-drift.yml` | — | Provider replay drift lane | Pending port; generated matrix/xwalk and breaking drift failure retained |
| `quality-debt-weekly.yml` | — | Retain disabled debt review policy | Do not activate job with existing if:false; local audits retained |
| `release.yml` | — | Protected release promotion lane | Pending port; approval and restricted PyPI/GHCR credentials |
| `reusable-mermaid-setup.yml` | — | Shared pinned Mermaid tooling | Pending consumer migration; keep lockfile scanned by OSV |
| `reusable-setup.yml` | — | CircleCI setup-python-uv | Prepared shared command; installer/cache/runtime parity pending |
| `root-hygiene.yml` | — | CircleCI root-hygiene | Prepared required gate; full-tree and remaining guards pending |
| `router-v7-bridge.yml` | — | Router bridge candidate acceptance | Pending port; managed host evidence remains separate |
| `schema-governance.yml` | — | CircleCI schema-governance | Prepared required gate; canonical generation/parity preserved |
| `scorecard.yml` | `30 7 * * 1` | Scorecard plus SARIF publication | Pending port; SARIF transport separate from CodeQL analysis |
| `security.yml` | — | CircleCI security-scans | Prepared required gate; unpatched braces blocks overall acceptance |
| `semantic-governance.yml` | — | Semantic governance audit lane | Pending port; not replaced by syntax validation |
| `skills-consistency.yml` | — | CircleCI skills-consistency | Prepared verify-only lane; doctor/support/event parity pending |
| `stale.yml` | — | GitHub API stale maintenance | Pending port; preserve exclusions and trusted write policy |
| `tests.yml` | — | CircleCI test-fast/test-integration | Prepared matrices; full source-bound producer/remote acceptance pending |
| `type-checking.yml` | — | CircleCI mypy | Prepared strict gate; final remote evidence pending |
| `vacuum.yml` | — | Local maintenance command | Retain manual/local operation; no automatic destructive schedule |
| `validate-vendored-mermaid-assets.yml` | — | Vendored tooling integrity lane | Pending port; preserve generated asset/hash guards |
| `zizmor.yml` | — | Remaining Actions YAML audit | Retain while composite action YAML exists; retirement depends on actual removal |

Local-only and intentionally disabled surfaces retain their operating policy;
disabled Actions stubs are not treated as missing credentials to be bypassed.
Triggers, contexts, approved publication and exact-SHA evidence remain cutover gates.

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
| `docker.yml` | Docker Build & Compose Validation | Optional Docker contract (ADR-010 adjunct), reproducible Trivy/SBOM baseline, blocking CRITICAL+HIGH+MEDIUM image gate, and no-rebuild promotion of the scanned image |
| `docs.yml` | Docs & Diagrams | MkDocs, links, Mermaid lint, targeted ChEMBL render, drift; `pr-required.yml` owner (re-enabled #10263) |
| `duplication-complexity.yml` | Duplication and Complexity Checks | Dup/complexity quality gates |
| `e2e-matrix-health.yml` | E2E Matrix Health | End-to-end matrix health |
| `github-settings-quarterly-review.yml` | Quarterly GitHub Settings Review | Read-only quarterly GitHub settings review |
| `import-linter.yml` | Lint and Architecture Gates | import-linter + layer architecture |
| `no-partial-tree-commits.yml` | No partial-tree commits | Rejects partial-tree commits before shared-history integration (#11709) |
| `opencode-pr-review.yml` | opencode-pr-review | Dispatch-only stub (#11012); remote OpenCode installer removed |
| `opencode-triage.yml` | opencode-triage | Dispatch-only stub (#11012); remote OpenCode installer removed |
| `pr-required.yml` | PR Gate Complete | Fail-closed coordinator; GitHub required context `pr-gate-complete` (ruleset 13643213, #10267) |
| `root-hygiene.yml` | Root Hygiene | Root allowlist / clutter gates |
| `router-v7-bridge.yml` | Router 7 bridge candidate | Candidate plugin, frontend and image parity checks; managed host acceptance remains separate |
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
| `diagram-nightly.yml` | Diagram Nightly Regression | `keep-disabled` |
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
