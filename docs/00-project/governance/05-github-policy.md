---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# GitHub Interaction Policy

*Synced with RULES.md v6.1.2 | Last updated: 2026-04-09*

----------------------------------------------------------------------

## Overview

This document defines how the BioETL project interacts with GitHub:
CI/CD pipelines, branch protection, code review, dependency management,
security scanning, release process, and issue/PR workflows.

----------------------------------------------------------------------

## 1. Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production-ready code | Required status checks, CODEOWNERS review |
| `develop` | Integration branch (optional) | Commit lint enforced |
| Feature branches | `feat/*`, `fix/*`, `refactor/*` | None |

### Branch Naming Convention

```
<type>/<short-description>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`

**Examples:**
- `feat/pubchem_compound-pipeline`
- `fix/chembl-rate-limit-429`
- `refactor/storage-clear-contract`

----------------------------------------------------------------------

## 2. CI/CD Workflows

BioETL uses **19 GitHub Actions workflows** organized by purpose.

### 2.1 Core Quality Gates (run on every PR)

| Workflow | File | Key Jobs | What It Checks |
|----------|------|----------|----------------|
| **Lint and Architecture Gates** | `import-linter.yml` | `lint`, `c901-governance`, `arch-tests`, `checks-complete` | Ruff lint+format, changed-file formatting enforcement, C901 baseline governance, architecture tests, import-linter, dependency boundary checks |
| **Tests** | `tests.yml` | `smoke-check`, `governance-preflight`, `config-schema-preflight`, `test-fast`, `test-matrix`, `coverage-verify`, `duration-telemetry` | VCR cassettes, config validation, governance preflight, smoke tests, fast unit feedback, full test matrix (Python 3.11+3.12, 6 groups), scoped pytest/Hypothesis cache fingerprints, final combined 85% coverage gate, slow-test telemetry artifact |
| **Type Checking (Strict)** | `type-checking.yml` | `type-check` | mypy strict, NewType/Protocol verification, `Any` usage analysis |
| **Commit Lint** | `commit-lint.yml` | `commit-lint` | Conventional Commits format enforcement |

### 2.2 Architecture & Schema Enforcement

| Workflow | File | Key Jobs | What It Checks |
|----------|------|----------|----------------|
| **Architecture Metrics** | `architecture.yml` | `architecture-fast-baseline`, `architecture-heavy-nightly` | Manual fast architecture gate and scheduled/on-demand heavy architecture + coverage profile |
| **Schema Governance** | `schema-governance.yml` | `generated-artifacts`, `contracts-export`, `schema-parity`, `schema-governance-status` | Generated schema artifacts up-to-date, contract imports, Domain-Silver-Gold parity |
| **Port Contract Tests** | `port-contracts.yml` | `port-contracts`, `hypothesis-contracts`, `contracts-status` | Port contract compliance, property-based testing (Hypothesis) |
| **Duplication & Complexity** | `duplication-complexity.yml` | `duplication-complexity`, `constructor-args-check`, `executor-complexity` | Radon CC, xenon grade limits (B max, A for domain), jscpd duplication, constructor arg counts |

### 2.3 Security

| Workflow | File | Key Jobs | What It Checks |
|----------|------|----------|----------------|
| **Security Scans** | `security.yml` | `detect-secrets`, `pip-audit` | Credential leak prevention, dependency vulnerability scanning |
| **Docker Build** | `docker.yml` | `docker-lint`, `docker-compose-validate`, `docker-build`, `docker-push` | Hadolint, compose syntax, Trivy image scanning (CRITICAL+HIGH), GHCR push on main |

### 2.4 Code Hygiene

| Workflow | File | Key Jobs | What It Checks |
|----------|------|----------|----------------|
| **Block Compiled Artifacts** | `compiled-artifacts-block.yml` | `no-pyc-check` | No `*.pyc` / `--pycache--` committed |
| **Root Hygiene** | `root-hygiene.yml` | `root-hygiene` | Repository root cleanliness audit |
| **Docs & Diagrams** | `docs.yml` | `docs-governance`, `validate-mkdocs`, `validate-mermaid`, `render-diagrams`, `check-diagram-drift` | Docs-only PR path, lightweight architecture doc-sync tests, strict MkDocs build, Mermaid syntax, diagram rendering, rendered-artifact drift checks |
| **Validate Mermaid** | `validate-mermaid.yml` | `check-mermaid` | Vendored Mermaid asset integrity |

### 2.5 Scheduled & On-Demand

| Workflow | File | Schedule | What It Does |
|----------|------|----------|--------------|
| **Mutation Testing** | `mutation-testing.yml` | Weekly (Sun 00:00 UTC) + PR | mutmut on domain layer, 70% mutation score threshold; application gate staged |
| **Contract Tests** | `contract-tests.yml` | Monthly (1st, 02:00 UTC) | Live API contract tests, creates GitHub issue on failure |
| **Weekly VACUUM** | `vacuum.yml` | Weekly (Sun 02:00 UTC) | Delta Lake VACUUM on all layers |
| **Release** | `release.yml` | On release publish | Build, test on 3 Python versions, publish to TestPyPI+PyPI |
| ~~Project Automation~~ | ~~`project-automation.yml`~~ | ~~Push + PR~~ | Removed: was a duplicate of `tests.yml` + `import-linter.yml` |

----------------------------------------------------------------------

## 3. Required Status Checks

For PRs to `main`, the following status checks **MUST** pass:

### Critical (blocking merge)

| Check Name | Workflow | Purpose |
|------------|----------|---------|
| `checks-complete` | import-linter.yml | Aggregates lint + C901 governance + architecture gates |
| `coverage-verify` | tests.yml | Combined 85% coverage threshold (matrix shards + serial pass) |
| `schema-governance-status` | schema-governance.yml | Schema parity and contracts |
| `detect-secrets` | security.yml | No credential leaks |
| `commit-lint` | commit-lint.yml | Conventional Commits |
| `type-check` | type-checking.yml | mypy strict compliance |

Docs-only PRs still go through blocking documentation governance via `docs.yml`:
the lightweight `docs-governance` job runs architecture doc-sync / drift tests
without pulling the full heavy test matrix into documentation-only changesets.

### Recommended (should be required)

| Check Name | Workflow | Purpose |
|------------|----------|---------|
| `contracts-status` | port-contracts.yml | Port contract compliance |
| `no-pyc-check` | compiled-artifacts-block.yml | No compiled artifacts |
| `root-hygiene` | root-hygiene.yml | Clean repository root |
| `docker-build` | docker.yml | Container builds successfully |

----------------------------------------------------------------------

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

| Path | Required Reviewers | Reason |
|------|--------------------|--------|
| `src/bioetl/domain/` | @SatoryKono | Domain purity, port contracts |
| `src/bioetl/composition/` | @SatoryKono | DI wiring, factory changes |
| `.github/workflows/` | @SatoryKono | CI/CD pipeline integrity |
| Everything else | @SatoryKono (default) | Project governance |

### Review Checklist

Every PR reviewer **MUST** verify:

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] No hardcoded secrets or credentials
- [ ] Architecture tests pass (`pytest tests/architecture/ -v`)
- [ ] Documentation updated if behavior changed
- [ ] Follows Conventional Commits format

----------------------------------------------------------------------

## 5. Dependency Management

### Dependabot

File: `.github/dependabot.yml`

| Ecosystem | Schedule | PR Limit | Labels |
|-----------|----------|----------|--------|
| pip (Python) | Weekly | 10 | `dependencies` |
| github-actions | Weekly | 5 | `ci` |

### Dependency Update Policy

| Priority | Action | SLA |
|----------|--------|-----|
| **Critical CVE** | Immediate patch | 24 hours |
| **High CVE** | Priority patch | 72 hours |
| **Medium CVE** | Normal update | Next sprint |
| **Routine updates** | Dependabot PR review | Weekly triage |

### Supply Chain Security

- All GitHub Actions **MUST** be SHA-pinned (e.g., `actions/checkout@<sha>`)
- Trivy scans Docker images for CRITICAL and HIGH vulnerabilities
- `pip-audit --strict` checks all Python dependencies
- `detect-secrets` prevents credential leaks in commits

----------------------------------------------------------------------

## 6. Issue & PR Templates

### Issue Templates

Located in `.github/ISSUE-TEMPLATE/`:

| Template | File | Labels |
|----------|------|--------|
| Bug Report | `bug-report.md` | `bug` |
| Feature Request | `feature-request.md` | `enhancement` |

### Pull Request Template

File: `.github/pull-request-template.md`

Every PR auto-populates with:
- Summary section
- Changes list
- Checklist (lint, test, secrets, arch, docs, conventional commits)

----------------------------------------------------------------------

## 7. Commit Convention

BioETL uses **Conventional Commits** (enforced by `commit-lint.yml`).

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Purpose | Example |
|------|---------|---------|
| `feat` | New feature | `feat(chembl): add assay pipeline` |
| `fix` | Bug fix | `fix(pubchem): handle 429 rate limit` |
| `refactor` | Code restructuring | `refactor(storage): extract delta writer` |
| `docs` | Documentation | `docs: update architecture diagram` |
| `test` | Test changes | `test(unit): add transformer coverage` |
| `chore` | Maintenance | `chore(deps): update httpx to 0.27` |
| `ci` | CI/CD changes | `ci: add pip-audit to security workflow` |

### Scopes

Common scopes: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`,
`semanticscholar`, `storage`, `domain`, `cli`, `deps`, `docker`

----------------------------------------------------------------------

## 8. Release Process

### Workflow: `release.yml`

Triggered by GitHub Release publication or manual dispatch.

```
1. Build         → wheel + sdist + twine verify
2. Test Install  → Python 3.11, 3.12, 3.13
3. TestPyPI      → Publish to test index
4. PyPI          → Publish to production index (releases only)
5. Assets        → Upload to GitHub Release
```

### Versioning

BioETL follows **Semantic Versioning** (SemVer):

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Breaking change | MAJOR | 5.0.0 -> 6.0.0 |
| New feature | MINOR | 6.0.0 -> 6.1.0 |
| Bug fix | PATCH | 6.1.0 -> 6.1.1 |

----------------------------------------------------------------------

## 9. Security Policy

Full security policy: [`.github/SECURITY.md`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/SECURITY.md)

### Key Points

- Secrets: Environment variables only (`BIOETL_{PROVIDER}_{KEY}`)
- VCR cassettes: Sanitized via `before-record` hooks
- Vulnerability reporting: security@example.com (72h response SLA)
- Automated scanning: detect-secrets, pip-audit, Trivy, Dependabot

----------------------------------------------------------------------

## 10. Workflow Permissions

All workflows follow the **least-privilege principle**:

```yaml
permissions:
  contents: read    # Default for most workflows
```

| Permission | Workflows That Use It |
|------------|----------------------|
| `contents: read` | All workflows (default) |
| `contents: write` | release.yml (asset upload) |
| `packages: write` | docker.yml (GHCR push) |
| `security-events: write` | docker.yml (Trivy SARIF upload) |
| `id-token: write` | release.yml (trusted publishing) |
| `issues: write` | contract-tests.yml (auto-create issue on failure) |

### Concurrency

All PR-triggered workflows use concurrency groups to cancel outdated runs:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

----------------------------------------------------------------------

## Quick Reference

### For Contributors

1. Fork/branch from `main`
2. Follow Conventional Commits
3. Ensure all CI checks pass
4. Request review (auto-assigned via CODEOWNERS)
5. Squash-merge after approval

### For Maintainers

1. Review CODEOWNERS paths on PRs
2. Triage Dependabot PRs weekly
3. Monitor monthly contract test results
4. Check mutation testing reports for domain coverage
5. Create releases via GitHub Releases UI

----------------------------------------------------------------------

*See also: [CONTRIBUTING.md](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/CONTRIBUTING.md) | [SECURITY.md](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/.github/SECURITY.md) | [RULES.md](../RULES.md)*
