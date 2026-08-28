______________________________________________________________________

Version: 1.2.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-27'

______________________________________________________________________

# GitHub Interaction Policy

*Synced with RULES.md and ADR-047 | Last updated: 2026-08-27*

______________________________________________________________________

## Overview

This document defines how the BioETL project interacts with GitHub:
CI/CD pipelines, branch protection, code review, dependency management,
security scanning, release process, and issue/PR workflows.

______________________________________________________________________

## 1. Branch Strategy

| Branch           | Purpose                         | Protection                                             |
| ---------------- | ------------------------------- | ------------------------------------------------------ |
| `main`           | Production-ready code           | Ruleset `root-hygiene-required-check` **active** (defined: `checks-complete` + `root-hygiene`; not GitHub-enforced). See §3. |
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
the integration (`dependabot/`, `renovate/`, `devin/`, `bolt/`). Human-created
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

BioETL uses **46 GitHub Actions workflows** (including reusable helper workflows). For the canonical file-level inventory, see [GitHub Actions Workflows](../../04-reference/github-actions-workflows.md).

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

Updates to `main` are blocked by live required-check ruleset `root-hygiene-required-check` (enforcement **active** for `refs/heads/main`). Direct
push and merge to `main` are blocked when `checks-complete` or `root-hygiene` fail. The following checks are the
enforced quality gate for pull requests and for the `main` ref.

### Final always-on required-check set

The final activation set for repository ruleset
`root-hygiene-required-check` is exactly the following two contexts:

| Check Name | Workflow | Why it is safe to require globally |
| --- | --- | --- |
| `checks-complete` | import-linter.yml | Unfiltered `pull_request` trigger; aggregates lint, C901 governance, architecture, and import-linter gates |
| `root-hygiene` | root-hygiene.yml | Unfiltered `pull_request` trigger; enforces repository-root governance |

Both checks materialize on every PR targeting `main`. The repository ruleset
`root-hygiene-required-check` remains defined with exactly this always-on set,
and enforcement is **active**. Direct push/merge to `main` is blocked when required checks fail. Further ruleset mutations remain external operations that require
explicit maintainer confirmation and API re-verification.

### Path-scoped core checks

The following checks remain required by policy whenever their workflow matches
the changed paths. They MUST NOT be configured as unconditional repository
required-status contexts until a separate decision makes their workflows
materialize on every PR; otherwise GitHub can leave a skipped required check
pending and block an unrelated PR.

| Check Name                 | Workflow              | Purpose                                                       |
| -------------------------- | --------------------- | ------------------------------------------------------------- |
| `coverage-verify`          | tests.yml             | Combined 85% coverage threshold (matrix shards + serial pass) |
| `schema-governance-status` | schema-governance.yml | Schema parity and contracts                                   |
| `detect-secrets`           | security.yml          | No credential leaks                                           |
| `commit-lint`              | commit-lint.yml       | Conventional Commits                                          |
| `type-check`               | type-checking.yml     | mypy strict compliance                                        |

Docs-only PRs should still go through documentation governance via `docs.yml`:
the lightweight `docs-governance` job runs architecture doc-sync / drift tests
without pulling the full heavy test matrix into documentation-only changesets.

### Architecture lane names (`architecture-full`)

`architecture-full` is the **non-slow** architecture gate. The three operator
surfaces below MUST stay 1:1 (same pytest marker expression). Do **not** brand
the slow sweep as `architecture-full`. Do **not** add `test-matrix` or
`coverage-verify` as unconditional GitHub required checks while those workflows
use `paths-ignore` (#9738, #9723).

| Surface | Name | Markers / command | GitHub required? |
| --- | --- | --- | --- |
| Pre-commit hook (manual) | `architecture-full` | `pytest tests/architecture/ -m "not slow and not benchmark and not memory"` | No (local `stages: [manual]`) |
| CI job | `arch-tests` in `import-linter.yml` | same markers | Only as part of `checks-complete` **if** ruleset enforcement is enabled (currently disabled, #9723) |
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

- **FAIL**: the gate is a required quality signal for PRs, but GitHub does not
  currently block merge or direct push. Failures MUST still be fixed or
  explicitly risk-accepted in the PR discussion. The defined always-on set
  remains `checks-complete` and `root-hygiene`.
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
| `root-hygiene.yml` | `gate.repo-hygiene` via `root-hygiene` | `.github/workflows/root-hygiene.yml` + disabled GitHub ruleset state |
| `docs.yml` | `gate.docs-governance` via `docs-governance` | `.github/workflows/docs.yml` + docs governance policy surfaces |
| `port-contracts.yml` | Supporting gate: `contracts-status` | `.github/workflows/port-contracts.yml` |
| `compiled-artifacts-block.yml` | Supporting gate: `no-pyc-check` | `.github/workflows/compiled-artifacts-block.yml` |
| `docker.yml` | Supporting gate: `docker-build` | `.github/workflows/docker.yml` |

### Branch Protection Verification

PR merges and direct pushes to `main` are not blocked by required status
checks. Repo-side evidence is the live repository ruleset state plus the
workflows that still materialize the recommended checks on pull requests.

Activated and re-verified on `2026-08-28` with repository admin credentials via the GitHub REST API (closeout for #9782).

Live GitHub enforcement state:

- Repository ruleset `root-hygiene-required-check` targets
  `refs/heads/main`.
- Enforcement: `active`.
- Direct updates to main are blocked by the active rule.
- Defined (inactive) required status checks: exactly `checks-complete` and `root-hygiene`
  (`strict_required_status_checks_policy: false`).
- The ruleset has no bypass actors (`current_user_can_bypass: never`).
- Classic branch protection on `main` is unused (HTTP 404). Rulesets are the
  SSOT; a 404 on `GET .../branches/main/protection` is expected.
- Applied rules on `main`: none (`[]`).
- Tracking references: `#3380`, `#8619`.
- Evidence: `https://github.com/SatoryKono/BioactivityDataAcquisition/rules/15730586`
- API: `GET /repos/SatoryKono/BioactivityDataAcquisition/rulesets/15730586`
- Applied rules: `GET /repos/SatoryKono/BioactivityDataAcquisition/rules/branches/main`

The legacy repository ruleset `main`
(`https://github.com/SatoryKono/BioactivityDataAcquisition/rules/13643213`)
remains **active** and is not part of the active gate set.

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

| Ecosystem      | Schedule | PR Limit | Labels         |
| -------------- | -------- | -------- | -------------- |
| pip (Python)   | Weekly   | 10       | `dependencies` |
| github-actions | Weekly   | 5        | `ci`           |

### Dependency Update Policy

| Priority            | Action               | SLA           |
| ------------------- | -------------------- | ------------- |
| **Critical CVE**    | Immediate patch      | 24 hours      |
| **High CVE**        | Priority patch       | 72 hours      |
| **Medium CVE**      | Normal update        | Next sprint   |
| **Routine updates** | Dependabot PR review | Weekly triage |

### Supply Chain Security

- All GitHub Actions **MUST** be SHA-pinned (e.g., `actions/checkout@<sha>`)
- `scripts/engineering/repo/check_github_actions_runtime_policy.py` enforces the
  pinned-action allowlist across `.github/workflows/**` and composite actions
  under `.github/actions/**`.
- Trivy records CRITICAL, HIGH, MEDIUM, and UNKNOWN findings and blocks the
  Docker image on CRITICAL, HIGH, or MEDIUM vulnerabilities
- `pip-audit --strict` checks all Python dependencies
- `detect-secrets` prevents credential leaks in commits

______________________________________________________________________

## 6. Issue & PR Templates

### Issue Templates

Located in `.github/ISSUE-TEMPLATE/`:

| Template        | File                 | Labels        |
| --------------- | -------------------- | ------------- |
| Bug Report      | `bug-report.md`      | `bug`         |
| Feature Request | `feature-request.md` | `enhancement` |

### Pull Request Template

File: `.github/pull-request-template.md`

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

Triggered by GitHub Release publication or manual dispatch.

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
It does not publish `:latest`. Environment protection (required reviewers or a
wait timer) can be added on `ghcr-publish` without changing the workflow.
| `id-token: write`        | release.yml (trusted publishing)                  |
| `issues: write`          | contract-tests.yml (auto-create issue on failure) |

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


### Evidence (2026-08-28)
```json
{
  "name": "root-hygiene-required-check",
  "enforcement": "active"
}
```

`Rollback: gh api -X PUT repos/SatoryKono/BioactivityDataAcquisition/rulesets/15730586 -f enforcement=disabled`
