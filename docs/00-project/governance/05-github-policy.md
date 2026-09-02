______________________________________________________________________

Version: 1.2.10
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-02'

______________________________________________________________________

# GitHub Interaction Policy

*Synced with RULES.md and ADR-047 | Last updated: 2026-09-02*

______________________________________________________________________

## Overview

This document defines how the BioETL project interacts with GitHub:
CI/CD pipelines, branch protection, code review, dependency management,
security scanning, release process, and issue/PR workflows.

______________________________________________________________________

## 1. Branch Strategy

| Branch           | Purpose                         | Protection                                             |
| ---------------- | ------------------------------- | ------------------------------------------------------ |
| `main`           | Production-ready code           | Ruleset `root-hygiene-required-check` **disabled** as of `2026-09-02` (`checks-complete`, `root-hygiene` still listed but not enforced). `pr-gate-complete` is the repo-side shadow coordinator after the atomic #9975 owner cutover — see §3. |
| `develop`        | Integration branch (optional)   | Commit lint enforced                                   |
| Feature branches | `feat/*`, `fix/*`, `refactor/*` | None                                                   |

### Branch Naming Convention

```
<type>/<short-description>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`

**Examples:**

- `feat/pubchem_compound-pipeline`
- `fix/chembl-rate-limit-429`
- `refactor/storage-clear-contract`

Automation-owned branches MAY use a provider prefix already established by
the integration (`dependabot/`, `renovate/`, `devin/`, `bolt/`, `copilot/`). Human-created
branches MUST use one of the project types above and a lowercase kebab-case
description. Opaque names (`a1`, `tmp`, numeric-only names), date-only names,
and persistent `backup/*` branches are non-compliant.

### Branch Lifecycle

| State | Required action | Retention |
| --- | --- | --- |
| Active PR or active worktree | Keep; never delete automatically | Until merged, closed, or explicitly abandoned |
| Merged branch | Delete after the merge commit is reachable from `main` | Within 7 days |
| Closed/unmerged branch | Owner review before deletion | Review after 30 days without activity |
| Release or durable recovery point | Create an annotated tag; do not retain a backup branch | Tags follow release retention |

Before deleting a local or remote branch, the operator MUST verify all of:

1. it is not `main`, a protected branch, an active PR head, or checked out by
   any worktree;
1. its tip and merge status were refreshed from GitHub rather than taken from
   a historical cleanup list;
1. unmerged branches have an explicit owner decision (`keep`, `tag`, or
   `delete`);
1. the cleanup command is reviewed in dry-run form before apply.

Branch-count ceilings MUST NOT be enforced by failing unrelated pull requests.
CI may reject the current PR head when its name violates this policy. Scheduled
branch inventory is report-only; deletion remains an explicit maintainer
operation. Cleanup tooling MUST default to dry-run and MUST NOT infer deletion
solely from age or a global branch-count target.

Compliant examples: `fix/vcr-lfs-preflight`, `ci/branch-name-policy`,
`docs/branch-lifecycle`. Non-compliant examples: `master_20260801`,
`backup-before-merge`, `12345`, `temp-fix`.

______________________________________________________________________

## 2. CI/CD Workflows

BioETL uses **48 GitHub Actions workflows** (including reusable helper workflows). For the canonical file-level inventory, see [GitHub Actions Workflows](../../04-reference/github-actions-workflows.md).

### 2.1 Core Quality Workflows

These workflows form the core quality surface, but their `pull_request`
filters differ. Section 3 distinguishes checks that materialize on every PR
from checks that run only for matching paths.

| Workflow                        | File                | Key Jobs                                                                                                                              | What It Checks                                                                                                                                                                                                                                      |
| ------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lint and Architecture Gates** | `import-linter.yml` | `lint`, `c901-governance`, `arch-tests`, `checks-complete`                                                                            | Ruff lint+format, changed-file formatting enforcement, C901 baseline governance, architecture tests, import-linter, dependency boundary checks                                                                                                      |
| **Tests**                       | `tests.yml`         | `smoke-check`, `governance-preflight`, `config-schema-preflight`, `test-fast`, `test-matrix`, `coverage-verify`, `duration-telemetry` | VCR cassettes, config validation, governance preflight, smoke tests, **3.12** fail-fast `test-fast` vs full test matrix (Python 3.13, 6 groups), scoped pytest/Hypothesis cache fingerprints, final combined 85% coverage gate, slow-test telemetry artifact. `test-matrix` is **not** a GitHub required check. |
| **Type Checking (Strict)**      | `type-checking.yml` | `type-check`                                                                                                                          | mypy strict, NewType/Protocol verification, `Any` usage analysis                                                                                                                                                                                    |
| **Commit Lint**                 | `commit-lint.yml`   | `commit-lint`                                                                                                                         | Conventional Commits format enforcement                                                                                                                                                                                                             |

### 2.2 Architecture & Schema Enforcement

| Workflow                     | File                         | Key Jobs                                                                               | What It Checks                                                                                |
| ---------------------------- | ---------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Architecture Metrics**     | `architecture.yml`           | `architecture-fast-baseline`, `architecture-heavy-nightly`                             | Manual fast architecture gate and scheduled/on-demand heavy architecture + coverage profile   |
| **Schema Governance**        | `schema-governance.yml`      | `generated-artifacts`, `contracts-export`, `schema-parity`, `schema-governance-status` | Generated schema artifacts up-to-date, contract imports, Domain-Silver-Gold parity            |
| **Port Contract Tests**      | `port-contracts.yml`         | `port-contracts`, `hypothesis-contracts`, `contracts-status`                           | Port contract compliance, property-based testing (Hypothesis)                                 |
| **Duplication & Complexity** | `duplication-complexity.yml` | `duplication-complexity`, `constructor-args-check`, `executor-complexity`              | Radon CC, xenon grade limits (B max, A for domain), jscpd duplication, constructor arg counts |

### 2.3 Security

| Workflow               | File                     | Key Jobs                                                                | What It Checks                                                                                          |
| ---------------------- | ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Security Scans**     | `security.yml`           | `detect-secrets`, `pip-audit`, `bandit`, `gitleaks`, `osv-scanner`      | Credential leak prevention, lockfile CVE scanning, Bandit, Gitleaks                                     |
| **Dependency review**  | `dependency-review.yml`  | `dependency-review`                                                     | PR-time HIGH/CRITICAL vulnerable dependency block on lockfile/manifest changes                          |
| **CodeQL**             | `codeql.yml`             | `analyze`                                                               | Python SAST uploaded to GitHub code scanning                                                            |
| **OpenSSF Scorecard**  | `scorecard.yml`          | `analysis`                                                              | Weekly non-blocking supply-chain scorecard baseline (SARIF to Security tab)                             |
| **zizmor**             | `zizmor.yml`             | `zizmor`                                                                | High-confidence GitHub Actions YAML audit on workflow/action changes                                    |
| **Docker Build**       | `docker.yml`             | `docker-lint`, `docker-compose-validate`, `docker-build`, `docker-push` | Hadolint, compose syntax, full Trivy evidence (CRITICAL+HIGH+MEDIUM+UNKNOWN), blocking CRITICAL+HIGH+MEDIUM gate, complete PR SBOM/baseline artifact; the exact scanned image is promoted without rebuild to GHCR on `main` via Environment `ghcr-publish` (`:sha` and `:ref_name` only, no `:latest`) |

### 2.3.1 CodeQL ownership and alert triage

BioETL uses **advanced CodeQL setup** owned by `.github/workflows/codeql.yml`.
GitHub code-scanning **default setup MUST remain `not-configured`**. Do not
enable default setup in parallel: that would duplicate Python scans and split
alert ownership.

| Item | Contract |
| --- | --- |
| Configuration owner | Advanced workflow `.github/workflows/codeql.yml` |
| Languages | Python only (`build-mode: none`) |
| Token permissions | Workflow `contents: read`; job `security-events: write` for SARIF upload |
| Cadence | Push/PR (docs-ignored paths excluded) plus weekly Monday `17 4 * * 1` UTC |
| Alert triage owner | BioETL Team (security lane); CODEOWNERS fallback `@SatoryKono` |
| Alert triage cadence | Weekly on Monday, together with OpenSSF Scorecard |
| Duplicate scans | Forbidden. Default setup stays off. |

Actionable CodeQL alerts get a follow-up issue the same triage week. Alerts are
closed only with SARIF/workflow proof, not by silent dismiss.

### 2.3.2 Residual OSV after RF-009 (#9853)

After supply-chain pin closeout (#9801) the BioETL **runtime image** (Wolfi/scratch)
stays Trivy-clean. OpenSSF Scorecard **Vulnerabilities** (check **#1294**) still
reports residual OSV/GHSA on **non-runtime** surfaces. That Scorecard check
**MUST remain open** until the packages are upgraded or this exception expires.
Do **not** add `osv-scanner.toml`, do **not** disable the Scorecard Vulnerabilities
check, and do **not** dismiss #1294 as a false green.

| ID | Package | Surface | Status until 2026-11-30 | Exposure |
| --- | --- | --- | --- | --- |
| GHSA-jmr9-qjv8-65gv | `extract-zip` | `.github/actions/setup-mermaid` via mermaid-cli 10.6.1 / puppeteer | Vendored 2.0.2 symlink-target patch (`vendor/extract-zip`); no upstream 2.x release | CI diagram render only |
| GHSA-5p4m-2wfm-xmqj | `js-yaml` | mermaid-cli lockfile | Pinned **4.3.2** (patched; `< 4.3.1` was affected) | CI diagrams |
| GHSA-2p49 / GHSA-xpqw | `svgo` | mermaid lockfile | Override **3.3.5** | CI diagrams |
| GHSA-8cj5 / pq67 / vj76 | `tar-fs` | mermaid puppeteer | Override **2.1.5** | CI diagrams |
| GHSA-3h5v / 58qx / 96hv | `ws` | mermaid puppeteer | Override **8.21.3** | CI diagrams |
| PYSEC-2026-3721 / CVE-2026-3219 | `pip==26.2.1` | `uv.lock` | Remediated 2026-08-31; `pip-audit --strict` is clean without `--ignore-vuln` | CI/dev extra; not runtime image |
| GHSA-2v37, 337j, wrjc, jjmj, 5c6j, qj8w, w5hq | Grafana npm (`react-router` 6.x, `uuid` 9.x, …) | `grafana/plugins/*` | No React Router 7 / uuid 11 force-bump (Grafana 13 host API) | Optional monitoring (ADR-010); not BioETL runtime |

Expiry: **2026-11-30**. Owner: BioETL Team. Accepted on #9853 (closed).
Re-triage: #9859. CI fail-closed gate:
`tests/architecture/test_residual_osv_9853.py::test_residual_osv_exception_has_not_expired`.
Upgrade mermaid-cli (keep diagram golden pins) and/or Grafana plugin majors, or
renew the exception with a new dated issue. Scorecard Vulnerabilities **#1294**
stays undismissed.

`security.yml` OSV-Scanner still scans `uv.lock` only and fails on HIGH/CRITICAL.
`pip-audit --strict` no longer ignores `PYSEC-2026-3721` / `CVE-2026-3219`
because `uv.lock` pins `pip==26.2.1`.

### 2.4 Code Hygiene

| Workflow                     | File                           | Key Jobs                                                                                           | What It Checks                                                                                                                                     |
| ---------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Block Compiled Artifacts** | `compiled-artifacts-block.yml` | `no-pyc-check`                                                                                     | No `*.pyc` / `--pycache--` committed                                                                                                               |
| **Root Hygiene**             | `root-hygiene.yml`             | `root-hygiene`                                                                                     | Repository root cleanliness audit                                                                                                                  |
| **Docs & Diagrams**          | `docs.yml`                     | `docs-governance`, `validate-mkdocs`, `validate-mermaid`, `render-diagrams`, `check-diagram-drift` | Docs-only PR path, lightweight architecture doc-sync tests, strict MkDocs build, Mermaid syntax, diagram rendering, rendered-artifact drift checks |
| **Validate vendored Mermaid assets** | `validate-vendored-mermaid-assets.yml` | `check-mermaid` | Vendored Mermaid asset presence check |

### 2.5 Scheduled & On-Demand

| Workflow               | File                         | Schedule                    | What It Does                                                                  |
| ---------------------- | ---------------------------- | --------------------------- | ----------------------------------------------------------------------------- |
| **Mutation Testing**   | `mutation-testing.yml`       | Weekly (Sun 00:00 UTC) + PR | mutmut on domain layer, 70% mutation score threshold; application gate staged |
| **Contract Tests**     | `contract-tests.yml`         | Monthly (1st, 02:00 UTC)    | Live API contract tests, creates GitHub issue on failure                      |
| **Weekly VACUUM**      | `vacuum.yml`                 | Weekly (Sun 02:00 UTC)      | Delta Lake VACUUM on all layers                                               |
| **Release**            | `release.yml`                | On release publish          | Build and test on Python 3.13, publish to TestPyPI+PyPI                      |
| `quality-debt-weekly.yml` | Weekly + manual dispatch | Debt scorecard and exemption-registry drift visibility |

______________________________________________________________________

## 3. Status Checks and Ruleset Contract

Updates to `main` **are currently NOT blocked** by repository ruleset `root-hygiene-required-check` (enforcement **disabled** as of `2026-09-02T09:24:27+03:00` for `main` (13643213) and `2026-09-02T09:41:27+03:00` for `root-hygiene-required-check` (15730586); see live evidence below). Direct
push and merge to `main` require the always-on contexts `checks-complete` and `root-hygiene`. There are no bypass actors (`current_user_can_bypass: never`). The following checks are the
GitHub-required quality gate for pull requests and for the `main` ref.

### Final always-on required-check set

The final activation set for repository ruleset
`root-hygiene-required-check` is exactly the following two contexts:

| Check Name | Workflow | Why it is safe to require globally |
| --- | --- | --- |
| `checks-complete` | import-linter.yml | Unfiltered `pull_request` trigger; aggregates lint, C901 governance, architecture, and import-linter gates |
| `root-hygiene` | root-hygiene.yml | Unfiltered `pull_request` trigger; enforces repository-root governance |

The legacy contexts remain saved in the disabled ruleset, but their leaf workflows
no longer own direct PR triggers after the atomic #9975 cutover. Every PR targeting
`main` now materializes the repo-side shadow coordinator `pr-gate-complete`, which
classifies the exact head SHA, invokes each reusable leaf owner once in a distinct
owner-namespaced concurrency group, and fails
closed on failure, cancellation, skip, missing result, invalid N/A evidence, or SHA
mismatch. Five-class shadow validation and the 20-run ambiguity/timing sample remain
required before #9979. Live ruleset enforcement remains `disabled`; any ruleset
mutation is an external admin operation requiring separate owner approval and fresh
API verification.

### Canonical CI owner map (#9974)

`configs/quality/github_required_checks.yaml` is the machine-readable source of
truth. A duplicate selector is forbidden unless that catalog records a distinct
purpose; the current catalog contains no allowed duplicate.

| Gate | Canonical workflow / job | Selector | Events | Artifacts | Status |
| --- | --- | --- | --- | --- | --- |
| Ruff | `import-linter.yml / lint` | `ruff check`, `ruff format --check` | coordinator PR, main push, call, manual | none | blocking |
| mypy | `type-checking.yml / type-check` | strict `mypy` | coordinator PR, main push, call, manual | failure report | blocking |
| dependency lock | `tests.yml / dependency-preflight` | `uv lock --check` | coordinator PR, main push, call, manual | failure report | blocking |
| architecture | `import-linter.yml / arch-tests` | non-slow architecture pytest lane | coordinator PR, main push, call, manual | architecture telemetry | blocking |
| integration | `tests.yml / test-matrix` | integration shard | coordinator PR, main push, call, manual | coverage/test telemetry | blocking |
| DQ consistency | `tests.yml / dq-consistency-gate` | `validate-dq-consistency` | coordinator PR, main push, call, manual | none | blocking |
| root hygiene | `root-hygiene.yml / root-hygiene` | root policy scan | coordinator PR, main push, call, manual | none | blocking |
| compiled artifacts | `compiled-artifacts-block.yml / no-pyc-check` | tracked bytecode scan | coordinator PR, main push, call | none | blocking |
| security | `security.yml` scanner jobs | secrets/dependency/SAST scanners | coordinator PR, main push, call | security reports | blocking |
| commit governance | `commit-lint.yml / commit-lint` | Conventional Commits | coordinator PR, call | none | blocking |
| docs governance | `docs.yml` governance jobs | documentation, MkDocs, diagram drift | coordinator PR, main push, call | rendered diagrams | blocking |
| canonical manifest hashes | `consolidation-gates.yml / canonical-manifest-hashes` | source/test SHA-256 manifests | manual | hash manifests | advisory evidence |

### Path-scoped core checks

The following leaf checks remain required by policy whenever the canonical
catalog classifies their changed paths as `required`. The always-materialized
coordinator emits an explicit, SHA-bound `not_applicable` decision otherwise;
raw leaf contexts MUST NOT be configured as unconditional repository required
statuses because the ruleset migration in #9979 will require only the final
`pr-gate-complete` context.

| Check Name                 | Workflow              | Purpose                                                       |
| -------------------------- | --------------------- | ------------------------------------------------------------- |
| `coverage-verify`          | tests.yml             | Combined 85% coverage threshold (matrix shards + serial pass) |
| `schema-governance-status` | schema-governance.yml | Schema parity and contracts                                   |
| `detect-secrets`           | security.yml          | No credential leaks                                           |
| `commit-lint`              | commit-lint.yml       | Conventional Commits                                          |
| `type-check`               | type-checking.yml     | mypy strict compliance                                        |

Docs-only PRs go through documentation governance via the reusable `docs.yml`
owner. Docker and schema owners materialize lightweight SHA-bound N/A jobs when
the catalog proves those lanes irrelevant; always-required quality/security
owners continue to run.

### Architecture lane names (`architecture-full`)

`architecture-full` is the **non-slow** architecture gate. The three operator
surfaces below MUST stay 1:1 (same pytest marker expression). Do **not** brand
the slow sweep as `architecture-full`. Do **not** add `test-matrix` or `coverage-verify` as
independent unconditional GitHub required checks; their results are consumed by `pr-gate-complete`
(#9738, #9723, #9975).

| Surface | Name | Markers / command | GitHub required? |
| --- | --- | --- | --- |
| Pre-commit hook (manual) | `architecture-full` | `pytest tests/architecture/ -m "not slow and not benchmark and not memory"` | No (local `stages: [manual]`) |
| CI job | `arch-tests` in `import-linter.yml` | same markers | Yes, as part of `checks-complete` in the active ruleset |
| `test_matrix` lane | `architecture` | same `marker_expression` | No |
| IDE daily | `pytest-architecture` | `architecture and not slow and not benchmark and not memory` | No |
| IDE / local slow | `pytest-architecture-slow-governance` | `architecture and not benchmark and not memory` (includes slow) | No |
| `test_matrix` slow lane | `architecture-slow-governance` | same as IDE slow | No (nightly / full audit; not PR `arch-tests`) |
| `tests.yml` job `test-matrix` | 6 path groups on Python **3.13** | not architecture | No (path-scoped; not always-on) |
| `tests.yml` job `test-fast` | unit-fast on Python **3.12** | fail-fast compatibility, no coverage | No |
| `coverage-verify` | combined 85% | `tests.yml` | Path-scoped only (§3 path-scoped table) |

`test-fast` (3.12, no coverage) and `test-matrix` unit shards (3.13, coverage)
share unit **paths** on purpose as a version split, not as two copies of the
same interpreter (#9740). Do not drop `coverage-verify`.

### Additional recommended checks

| Check Name         | Workflow                     | Purpose                       |
| ------------------ | ---------------------------- | ----------------------------- |
| `contracts-status` | port-contracts.yml           | Port contract compliance      |
| `no-pyc-check`     | compiled-artifacts-block.yml | No compiled artifacts         |
| `docker-build`     | docker.yml                   | Container builds successfully |

### Unified quality gates (canonical names)

To remove drift between workflow-specific job names and governance language, BioETL uses these canonical gate names:

| Canonical Gate | Required check job(s) | Fail/Warn rule |
| --- | --- | --- |
| `gate.lint-arch` | `checks-complete` | **FAIL** on any lint/C901/architecture/import-linter failure |
| `gate.tests-coverage` | `coverage-verify` | **FAIL** when combined coverage threshold is not met |
| `gate.types` | `type-check` | **FAIL** on mypy strict errors |
| `gate.schema-contracts` | `schema-governance-status` | **FAIL** on schema parity/contract export drift |
| `gate.security-secrets` | `detect-secrets` | **FAIL** on secret findings |
| `gate.commit-policy` | `commit-lint` | **FAIL** on non-Conventional Commit messages |
| `gate.repo-hygiene` | `root-hygiene` | **FAIL** on root policy violations |
| `gate.docs-governance` | `docs-governance` (docs-only changesets) | **WARN→FAIL escalation**: warn for non-blocking drift, fail for contract/governance breakage |

### Escalation policy for fail/warn

- **FAIL**: failures in `checks-complete` and `root-hygiene` fail those
  workflows and **block** merge or direct push while ruleset enforcement is
  `active`. Failures in other policy gates MUST still
  be fixed or explicitly risk-accepted in the PR discussion.
- **WARN**: merge MAY proceed only with documented justification and a follow-up issue with owner and due date.
- **WARN→FAIL**: repeated warning in 2 consecutive runs for the same surface, or warning on governance-contract surfaces (`RULES.md`, ADR-linked checks, schema parity, secrets) escalates to FAIL.

### Workflow → Gate → Source of truth

| Workflow file | Gate(s) surfaced | Source of truth |
| --- | --- | --- |
| `import-linter.yml` | `gate.lint-arch` via `checks-complete` | `.github/workflows/import-linter.yml` (job IDs) + this policy section |
| `tests.yml` | `gate.tests-coverage` via `coverage-verify` | `.github/workflows/tests.yml` + this policy section |
| `type-checking.yml` | `gate.types` via `type-check` | `.github/workflows/type-checking.yml` + this policy section |
| `schema-governance.yml` | `gate.schema-contracts` via `schema-governance-status` | `.github/workflows/schema-governance.yml` + this policy section |
| `security.yml` | `gate.security-secrets` via `detect-secrets` | `.github/workflows/security.yml` + this policy section |
| `commit-lint.yml` | `gate.commit-policy` via `commit-lint` | `.github/workflows/commit-lint.yml` + this policy section |
| `root-hygiene.yml` | `gate.repo-hygiene` via `root-hygiene` | `.github/workflows/root-hygiene.yml` + live GitHub ruleset state |
| `docs.yml` | `gate.docs-governance` via `docs-governance` | `.github/workflows/docs.yml` + docs governance policy surfaces |
| `port-contracts.yml` | Supporting gate: `contracts-status` | `.github/workflows/port-contracts.yml` |
| `compiled-artifacts-block.yml` | Supporting gate: `no-pyc-check` | `.github/workflows/compiled-artifacts-block.yml` |
| `docker.yml` | Supporting gate: `docker-build` | `.github/workflows/docker.yml` |

### Branch Protection Verification

PR merges and direct pushes to `main` **are** blocked by repository
ruleset `root-hygiene-required-check` while enforcement is active. Repo-side evidence is the live
repository ruleset state plus the workflows that materialize
`checks-complete` and `root-hygiene` on pull requests.

Activated and re-verified on `2026-08-28` with repository admin credentials via the GitHub REST API (closeout for #9782). Re-verified disabled on `2026-08-30` via the GitHub REST API (maintainer request during 72h branch consolidation). Re-activated on `2026-08-31` via the GitHub REST API (closeout for #9800; owner-approved required-check set). On `2026-09-01`, strict up-to-date enforcement was enabled and the companion `main` ruleset was activated for deletion and non-fast-forward protection.

Live GitHub enforcement state (as of `2026-09-02`, `main@1b8f4edabb`):

- Repository ruleset `root-hygiene-required-check` (15730586) targets
  `refs/heads/main`.
- Enforcement: `disabled` (was `active` until `2026-09-02T09:41:27+03:00`).
- Companion ruleset `main` (13643213) targets `refs/heads/main`.
- Enforcement: `disabled` (was `active` until `2026-09-02T09:24:27+03:00`).
- `pr-gate-complete` runs on every PR targeting `main` as shadow evidence after the atomic #9975 cutover; it is not yet a required status check.
- Legacy required contexts still listed in disabled rulesets: `checks-complete`, `root-hygiene`.
- Direct updates to main are blocked by this ruleset when required checks are missing or failing.
- Defined status checks: exactly `checks-complete` and `root-hygiene`
  (`strict_required_status_checks_policy: true`).
- The ruleset has no bypass actors (`current_user_can_bypass: never`).
- Classic branch protection on `main` is unused (HTTP 404). Rulesets are the
  SSOT; a 404 on `GET .../branches/main/protection` is expected.
- Applied rules on `main`: required status checks from ruleset `15730586`;
  deletion and non-fast-forward protection from ruleset `13643213`.
- Tracking references: `#3380`, `#8619`, `#9800`, Scorecard `#1272`.
- Evidence: `https://github.com/SatoryKono/BioactivityDataAcquisition/rules/15730586`
- API: `GET /repos/SatoryKono/BioactivityDataAcquisition/rulesets/15730586`
- Applied rules: `GET /repos/SatoryKono/BioactivityDataAcquisition/rules/branches/main`

The companion repository ruleset `main`
(`https://github.com/SatoryKono/BioactivityDataAcquisition/rules/13643213`)
targets `refs/heads/main`, is **active**, and has exactly the `deletion` and
`non_fast_forward` rules with no bypass actors. It intentionally omits required
signatures and pull-request approvals: the repository currently has one direct
collaborator, so an independent-approval requirement would create a governance
deadlock. Scorecard CodeReview alert `#1295` therefore remains open.

For a stale classic branch-protection context left after disconnecting an
external GitHub App, preview the bounded maintenance helper with
`bash scripts/ops/maintenance/github/remove_required_status_check.sh --dry-run`.
It does not edit rulesets; use the GitHub ruleset settings or API for those.

Repeat this verification at least quarterly and after any branch-protection or
ruleset migration.

______________________________________________________________________

## 4. Code Review & CODEOWNERS

### CODEOWNERS

File: `.github/CODEOWNERS`

```
# Default owner for all files
* @SatoryKono

# Architecture-critical paths
src/bioetl/domain/       @SatoryKono
src/bioetl/composition/  @SatoryKono
.github/workflows/       @SatoryKono
```

### Review Rules

| Path                      | Required Reviewers    | Reason                        |
| ------------------------- | --------------------- | ----------------------------- |
| `src/bioetl/domain/`      | @SatoryKono           | Domain purity, port contracts |
| `src/bioetl/composition/` | @SatoryKono           | DI wiring, factory changes    |
| `.github/workflows/`      | @SatoryKono           | CI/CD pipeline integrity      |
| Everything else           | @SatoryKono (default) | Project governance            |

### Review Checklist

Every PR reviewer **MUST** verify:

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] No hardcoded secrets or credentials
- [ ] Architecture tests pass (`pytest tests/architecture/ -v`)
- [ ] Documentation updated if behavior changed
- [ ] Follows Conventional Commits format

______________________________________________________________________

## 5. Dependency Management

### Dependabot

File: `.github/dependabot.yml`

| Ecosystem      | Schedule | PR Limit | Labels            | Grouping                |
| -------------- | -------- | -------- | ----------------- | ----------------------- |
| pip (Python)   | Weekly   | 10       | `dependencies`    | `pip-minor-patch` (minor+patch) |
| github-actions | Weekly   | 5        | `ci/cd`           | `github-actions` (all)  |
| docker         | Weekly   | 5        | `dependencies,ci/cd` | `docker` (all)        |
| npm (`/`) | Weekly | 5 | `dependencies` | `npm-root` |
| npm (`/.github/actions/setup-mermaid`) | Weekly | 5 | `dependencies,ci/cd` | `npm-mermaid` |
| npm (`/.github/tooling/jscpd`) | Weekly | 5 | `dependencies,ci/cd` | `npm-jscpd` |
| npm (`/grafana/plugins/bioetl-scenes-app`) | Weekly | 5 | `dependencies` | `npm-grafana-scenes` |
| npm (`/grafana/plugins/bioetl-selectorshell-panel`) | Weekly | 5 | `dependencies` | `npm-grafana-selectorshell` |

Minor/patch grouping keeps weekly PR volume manageable; security-relevant major bumps stay as individual PRs for review.

Triage owner: `@SatoryKono` (CODEOWNERS fallback), weekly cadence. Critical CVE ≤ 24h, High ≤ 72h — see SLA table below and `.github/SECURITY.md`.
Dependabot creates update PRs; repository-level **Dependabot alerts + security updates** must be enabled separately in GitHub Settings → Code security (not just `dependabot.yml`). Security PRs must pass all project checks; auto-merge is forbidden.

### Dependency Update Policy

| Priority            | Action               | SLA           |
| ------------------- | -------------------- | ------------- |
| **Critical CVE**    | Immediate patch      | 24 hours      |
| **High CVE**        | Priority patch       | 72 hours      |
| **Medium CVE**      | Normal update        | Next sprint   |
| **Routine updates** | Dependabot PR review | Weekly triage |

### Supply Chain Security

- All GitHub Actions **MUST** be full-SHA-pinned (`owner/action@<40-hex>` with ` # vX.Y.Z` comment) — tag references are rejected by the enforcer and by the repository Actions setting `sha_pinning_required` when enabled. Local `./` actions are exempt.
- `scripts/engineering/repo/check_github_actions_runtime_policy.py` enforces the
  pinned-action allowlist (`ALLOWED_USES`) across `.github/workflows/**` and composite actions
  under `.github/actions/**`, plus `configs/quality/github_actions_remote_artifacts.yaml` for remote `curl|wget … | sh` patterns.
- Updating a pinned Action: bump the workflow SHA **and** add the new SHA to `ALLOWED_USES` (keep the ` # vX.Y.Z` comment), then run `python -m scripts.engineering.repo check-actions-runtime-policy` and `pytest tests/architecture/test_github_actions_runtime_policy.py`. zizmor (`zizmor.yml`) runs as high-confidence gate on workflow/action changes.
- Trivy records CRITICAL, HIGH, MEDIUM, and UNKNOWN findings and blocks the
  Docker image on CRITICAL, HIGH, or MEDIUM vulnerabilities
  - Residual OSV accepted per #9853 (expiry **2026-11-30**, re-triage #9859): GHSA `jMR9-qjv8-65gv` (extract-zip 2.0.2 via mermaid-cli 10.6.1 `overrides`), `5p4m-...` (js-yaml 4.3.2), `svgo 3.3.5`, `tar-fs 2.1.5`, `ws 8.21.3`, Grafana `react-router/uuid`. `PYSEC-2026-3721` / `CVE-2026-3219` is remediated at `pip==26.2.1` (no `--ignore-vuln`). Scorecard Vulnerabilities #1294 stays **undismissed**; CI fail-closed `tests/architecture/test_residual_osv_9853.py::test_residual_osv_exception_has_not_expired`; do **not** add `osv-scanner.toml` and do **not** dismiss #1294.
- `pip-audit --strict` checks all Python dependencies
- `detect-secrets` prevents credential leaks in commits

______________________________________________________________________

## 6. Issue & PR Templates

### Issue Templates

Located in `.github/ISSUE_TEMPLATE/`. GitHub Issue Forms are the sole active
intake format:

| Form | File | Labels | Role |
| --- | --- | --- | --- |
| Bug Report | `bug_report.yml` | `bug` | Primary |
| Feature Request | `feature_request.yml` | `enhancement` | Primary |
| Retention-Sensitive Cleanup | `retention_sensitive_cleanup.yml` | `cleanup,guardrails` | Specialized |

`config.yml` disables blank issues and routes vulnerability reports to
private Security Advisories. The two `*.md` files are inactive migration
references without YAML front matter and are retained until the label/template
migration review completes.

### Labels and Wiki

The canonical classifications, migration window, automation consumers, Issue
Forms ownership, and the decision to disable GitHub Wiki are defined in
[GitHub label taxonomy, intake, and Wiki ownership](github-label-taxonomy.md)
and `configs/quality/github_governance_policy.json`. Unknown labels default to
`retained`; label deletion requires the documented human review and MUST NOT
occur before 2026-11-30.

### Quarterly settings review

`.github/workflows/github-settings-quarterly-review.yml` performs a read-only
review on the first day of each quarter and on manual dispatch. It discovers
the repository/default branch dynamically, writes evidence, and does not edit
settings, secrets, branches, labels, environments, or issues. Follow
[Quarterly read-only GitHub settings review](../../05-operations/runbooks/github-settings-quarterly-review.md)
for escalation and evidence requirements.

### Pull Request Template

File: `.github/pull_request_template.md`

Every PR auto-populates with:

- Summary section
- Changes list
- Checklist (lint, test, secrets, arch, docs, conventional commits)

______________________________________________________________________

## 7. Commit Convention

BioETL uses **Conventional Commits** (enforced by `commit-lint.yml`).

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type       | Purpose            | Example                                   |
| ---------- | ------------------ | ----------------------------------------- |
| `feat`     | New feature        | `feat(chembl): add assay pipeline`        |
| `fix`      | Bug fix            | `fix(pubchem): handle 429 rate limit`     |
| `refactor` | Code restructuring | `refactor(storage): extract delta writer` |
| `docs`     | Documentation      | `docs: update architecture diagram`       |
| `test`     | Test changes       | `test(unit): add transformer coverage`    |
| `chore`    | Maintenance        | `chore(deps): update httpx to 0.27`       |
| `ci`       | CI/CD changes      | `ci: add pip-audit to security workflow`  |

### Scopes

Common scopes: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`,
`semanticscholar`, `storage`, `domain`, `cli`, `deps`, `docker`

______________________________________________________________________

## 8. Release Process

### Workflow: `release.yml`

Triggered by GitHub Release publication or manual dispatch (`workflow_dispatch` with `dry_run` default `true`).

Environments: `testpypi` (`if: release || (workflow_dispatch && dry_run == 'false')`) and `pypi` (`if: release` only, `needs: publish-testpypi` chain). Both use OIDC trusted publishing (`id-token: write`, `pypa/gh-action-pypi-publish`). Configure deployment branch policy (tags/releases only for `pypi`) and a reviewer/wait-timer in GitHub Settings → Environments; repository docs do not replace the live protection rule.

```
1. Build         → wheel + sdist + twine verify
2. Test Install  → Python 3.13
3. TestPyPI      → Publish to test index
4. PyPI          → Publish to production index (releases only)
5. Assets        → Upload to GitHub Release
```

### Versioning

BioETL follows **Semantic Versioning** (SemVer):

| Change Type     | Version Bump | Example        |
| --------------- | ------------ | -------------- |
| Breaking change | MAJOR        | 5.0.0 -> 6.0.0 |
| New feature     | MINOR        | 6.0.0 -> 6.1.0 |
| Bug fix         | PATCH        | 6.1.0 -> 6.1.1 |

______________________________________________________________________

## 9. Security Policy

Full security policy: [`.github/SECURITY.md`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/SECURITY.md)

### Key Points

- Secrets: Environment variables only (`BIOETL_{PROVIDER}_{KEY}`)
- VCR cassettes: Sanitized via `before-record` hooks
- Vulnerability reporting: GitHub Security Advisories private reporting for this repository (72h response SLA)
- Automated scanning: detect-secrets, pip-audit, Trivy, Dependabot

______________________________________________________________________

## 10. Workflow Permissions

All workflows follow the **least-privilege principle**:

```yaml
permissions:
  contents: read    # Default for most workflows
```

| Permission               | Workflows That Use It                             |
| ------------------------ | ------------------------------------------------- |
| `contents: read`         | All workflows (default)                           |
| `contents: write`        | release.yml (asset upload)                        |
| `packages: write`        | docker.yml `docker-push` (GHCR; Environment `ghcr-publish`) |
| `security-events: write` | docker.yml (Trivy SARIF upload)                   |

`docker-push` publishes GHCR images only from `main` pushes, through Environment
`ghcr-publish`, with tags `:${{ github.sha }}` and `:${{ github.ref_name }}`.
It does not publish `:latest`. The live `ghcr-publish` environment requires
review by `@SatoryKono` and accepts only the `main` branch.
Non-`main` branches cannot reach the job — `docker.yml: if: github.ref == 'refs/heads/main' && github.event_name == 'push'`.
| `id-token: write`        | release.yml (trusted publishing via `pypi`/`testpypi` environments; see §8) |
| `issues: write`          | contract-tests.yml (auto-create issue on failure) |

Live publishing/deployment environment controls (API-verified 2026-08-30):

| Environment | Owner / reviewer | Allowed refs | Purpose |
| --- | --- | --- | --- |
| `ghcr-publish` | `@SatoryKono` | branch `main` | `docker.yml` → immutable SHA/ref-name GHCR tags |
| `observability-render-host` | `@SatoryKono` | branch `main` | reviewed manual execution on the self-hosted render runner |
| `testpypi` | `@SatoryKono` | branch `main`; tags `v*` | reviewed manual dry-run override or release OIDC publish |
| `pypi` | `@SatoryKono` | tags `v*` | release-only OIDC publish after `testpypi` |

Each listed environment has a required-reviewer rule and a custom deployment
branch/tag policy. Self-review remains allowed because the repository currently
has one maintainer; this prevents deployment lockout while retaining an explicit
approval gate. The environment-secret inventory was empty at verification time;
PyPI uses OIDC trusted publishing. `copilot` and `staging` are not referenced by
tracked workflows and have no environment secrets, so they are not classified
as write-capable deployment surfaces. Environment secrets, if later added, must
be scoped/rotated and never echoed in logs.

`contract-tests.yml` keeps `contents: read` as the workflow baseline and grants
`issues: write` only to the live contract-test job that creates a failure issue.

### Concurrency

All PR-triggered workflows use concurrency groups to cancel outdated runs:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Required push workflows on `main` (Tests, Lint and Architecture Gates, CodeQL)
MUST NOT share a ref-wide group. Queued runs for an older SHA are otherwise
discarded when a newer `main` SHA arrives, even with `cancel-in-progress: false`.
Those three workflows use:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.sha }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

______________________________________________________________________

## Quick Reference

### For Contributors

1. Fork/branch from `main`
1. Follow Conventional Commits
1. Ensure all CI checks pass
1. Request review (auto-assigned via CODEOWNERS)
1. Squash-merge after approval

### For Maintainers

1. Review CODEOWNERS paths on PRs
1. Triage Dependabot PRs weekly
1. Monitor monthly contract test results
1. Check mutation testing reports for domain coverage
1. Create releases via GitHub Releases UI

______________________________________________________________________

*See also: [CONTRIBUTING.md](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/CONTRIBUTING.md) | [SECURITY.md](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/SECURITY.md) | [RULES.md](../RULES.md)*


### Main rulesets (RF-008 / GH-RULESET-001 — required checks and ref protection active)

Target: `refs/heads/main` (ruleset `15730586` `root-hygiene-required-check`).
Rules currently enforced: required status checks `[checks-complete, root-hygiene]` (`strict_required_status_checks_policy:true`). Companion ruleset `13643213` `main` enforces `deletion` and `non_fast_forward` protection on the same ref. Both rulesets have no bypass actors (`current_user_can_bypass: never`). Additional review/linear-history/signature rules remain out of these rulesets. Rollback requires an explicitly approved PUT for the affected ruleset and a new entry in §3 Evidence. Tracking: Scorecard #1272 (BranchProtection), #1295 (CodeReview), #1296 (CIIBestPractices).

### Quarterly Read-Only Review Runbook (read-only, no mutations)

Owner: @SatoryKono · Cadence: quarterly · Last: 2026-08-28 → Next: 2026-11-28 · Due: +5 days after quarter (Q4 due `2026-12-05`, cron `23 6 1 1,4,7,10`) · Evidence: `reports/governance/quarterly-review-YYYY-QN.md` + `reports/quality/github-settings-review*.json` (30d retention, `automation_mutated_github:false`).

Checklist (read-only `GET`, `--paginate` where paginated, no `PUT/PATCH/POST/DELETE`):
`GET /repos/{owner}/{repo}/rulesets` → `GET /rulesets/{id}` (15730586 and 13643213 both active) → `GET /rules/branches/main` (required status checks when 15730586 is active) → `GET /code-scanning/alerts?per_page=100` → `GET /labels?per_page=100 --paginate` (209 labels) → `GET /repos/{repo} --jq '{has_wiki,default_branch}'`.
Escalation: drift → open/update governance issue (high-risk → Security lane/Release engineering day of review); do not expand token scopes.
Verification (no token, dry-run): `pytest tests/architecture/test_github_governance_review.py` (`READ_ONLY_GH_COMMANDS` + `workflow_dispatch` + `cron 23 6 1 1,4,7,10`).

### Evidence (2026-08-28)

```json
{
  "name": "root-hygiene-required-check",
  "enforcement": "active"
}
```

### Evidence (2026-08-30)

```json
{
  "name": "root-hygiene-required-check",
  "enforcement": "disabled"
}
```

### Evidence (2026-09-02) — live disabled + shadow aggregator

```json
{
  "rulesets": [
    {"id": 13643213, "name": "main", "enforcement": "disabled", "updated_at": "2026-09-02T09:24:27.854+03:00"},
    {"id": 15730586, "name": "root-hygiene-required-check", "enforcement": "disabled", "updated_at": "2026-09-02T09:41:27.708+03:00"}
  ],
  "required_status_checks": ["checks-complete", "root-hygiene"],
  "aggregator_shadow": {"context": "pr-gate-complete", "workflow": ".github/workflows/pr-required.yml", "materializes_on": "every pull_request targeting main", "enforcement": "not shadow-validated", "catalog": "configs/quality/github_required_checks.yaml"}
}
```

`Re-enable: gh api --method PUT repos/SatoryKono/BioactivityDataAcquisition/rulesets/15730586` with `enforcement=active`

### Evidence (2026-08-31)

```json
{
  "name": "root-hygiene-required-check",
  "enforcement": "active",
  "bypass_actors": [],
  "current_user_can_bypass": "never",
  "required_status_checks": ["checks-complete", "root-hygiene"]
}
```

Merge-block proof: `PUT /repos/SatoryKono/BioactivityDataAcquisition/pulls/9895/merge` returned HTTP 405 `Required status check "checks-complete" is expected.` while ruleset 15730586 was `active`.

### Evidence (2026-09-01)

```json
{
  "rulesets": [
    {
      "id": 15730586,
      "name": "root-hygiene-required-check",
      "enforcement": "active",
      "strict_required_status_checks_policy": true,
      "required_status_checks": ["checks-complete", "root-hygiene"],
      "bypass_actors": []
    },
    {
      "id": 13643213,
      "name": "main",
      "enforcement": "active",
      "include": ["refs/heads/main"],
      "rules": ["deletion", "non_fast_forward"],
      "bypass_actors": []
    }
  ]
}
```

### Migration notes (1.2.2)

- Changed `root-hygiene-required-check` from defined-only, disabled enforcement
  to active GitHub enforcement on `refs/heads/main`.
- Preserved the required contexts `checks-complete` and `root-hygiene` and
  disabled the legacy `main` ruleset.
- Related decision context: [ADR-047: Workflow Control Plane for Declarative
  Workflows](../../02-architecture/decisions/ADR-047-workflow-control-plane.md).

### Migration notes (1.2.3)

- Re-verified live API state on `2026-08-30`: both `root-hygiene-required-check`
  (15730586) and legacy `main` (13643213) have `enforcement: disabled`.
- Policy SSOT now matches that live state. Workflows still emit
  `checks-complete` and `root-hygiene`; they are not GitHub-required while the
  ruleset is disabled.

### Migration notes (1.2.4)

- Documented residual OSV exception #9853 (expiry 2026-11-30) for mermaid-cli
  puppeteer, Grafana plugins, and `PYSEC-2026-3721` / `CVE-2026-3219`.
- Scorecard Vulnerabilities check #1294 stays undismissed; `osv-scanner.toml`
  remains forbidden.

### Migration notes (1.2.5)

- #9853 closeout: residual OSV exception is accepted. Re-triage moved to #9859.
  CI fails closed after 2026-11-30
  (`test_residual_osv_exception_has_not_expired`). Scorecard #1294 remains
  undismissed.

### Migration notes (1.2.6)

- #9859 re-triage: `pip==26.2.1` remediates `PYSEC-2026-3721` / `CVE-2026-3219`;
  `pip-audit --strict` no longer uses `--ignore-vuln`. Mermaid-cli 10.6.1
  vendored `extract-zip` 2.0.2 and Grafana plugin residuals remain until
  2026-11-30. Scorecard #1294 stays undismissed.

### Migration notes (1.2.7)

- #9800 closeout: ruleset `15730586` `root-hygiene-required-check` is `active`
  on `refs/heads/main` with required contexts `checks-complete` and
  `root-hygiene`, no bypass actors. Rollback remains `enforcement=disabled`.

### Migration notes (1.2.8)

- Scorecard #1272 partial remediation: activated ruleset `13643213` on
  `refs/heads/main` with only deletion and non-fast-forward protection.
- Enabled strict up-to-date policy for the existing required contexts in
  ruleset `15730586`; no bypass actors were added.
- Scorecard #1295 stays open because the live repository has one direct
  collaborator and an independent-approval rule would deadlock maintenance.

### Migration notes (1.2.9)

- #9975 repo-side cutover: `pr-gate-complete` now materializes on every pull
  request targeting `main` and owns one reusable invocation per catalog gate.
- Direct PR triggers were removed from the twelve called leaf workflows in the
  same change; their push, schedule, and manual triggers remain intact. Reusable
  concurrency groups use owner-specific prefixes because `github.workflow`
  resolves to the common caller name inside called workflows.
- The coordinator uses exact-head classification, explicit SHA-bound N/A
  evidence, and fail-closed aggregation. Rulesets remain unchanged and disabled;
  #9979 still requires five-class shadow evidence, 20 unambiguous runs, timing
  confirmation from streams 1 and 3, and separate owner approval.
