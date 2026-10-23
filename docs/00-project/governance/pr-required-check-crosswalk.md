# PR Required Check & Governance Compatibility Crosswalk

**Date:** 2026-10-23
**Issue:** #12370
**Objective:** Audit PR required-check enforcement, workflow skip semantics, and governance compatibility.

## 1. Required Checks Enforcement (API Evidence)

Based on the latest check (2026-10-22 API read):
- **Ruleset ID:** `13643213`
- **Status:** `disabled`
- **Notes:** Current GitHub API configuration for `main` does not enforce active required checks. Legacy contexts (`ci/circleci`) are present. `pr-gate-complete` in GitHub Actions is not actively protecting the default branch.

## 2. CI/CD Architecture & Flow

- **Primary PR Aggregator:** `pr-gate-complete` in `.github/workflows/pr-required.yml`
- **Tests Execution:** The `tests.yml` handles `test-fast` (fail-fast on Python 3.12) and `test-matrix` (Python 3.13, 6 groups). However, `test-matrix` is NOT a leaf required check for all PRs (due to path scoping).
- **Coverage Gate:** `coverage-verify` enforces a combined 85% threshold, run by the nightly coordinator, and not natively blocking via GitHub PR required checks unless properly bound.

## 3. Governance Crosswalk Matrix

| Standard/ADR | Context / Invariant | Validation / Required Check Compatibility | Notes |
|---|---|---|---|
| **ADR-040** | Diagram governance | Nightly workflows (`diagram-nightly.yml`) build diagrams, PR gates validate artifact schema/freshness. | Architecture invariant maintained. Fast check passes without full rerun. |
| **ADR-042** | Testing Strategy Matrix | Matrix covers E2E, Unit, Smoke. Smoke checks (`chembl-baseline-smoke.yml`) and `test-fast` provide fail-fast. | Ensures path filtering doesn't bypass critical assertions. |
| **ADR-043** | Documentation Knowledge Management | Docs updates don't trigger test matrix (`docs.yml` only). | Scope bounding preserves resources while keeping docs fresh. |
| **RULES.md** | Core production rules | Enforced through `pr-required.yml` (e.g. `Ruff check`, `mypy` strict). | No unintended bypass permitted. |

## 4. Stability and Security Audit

- **Skip Semantics:** Path filtering isolates doc changes from code tests successfully.
- **Least Privileges:** Actions permissions mapped correctly. `pull_request` context avoids secret exposure compared to `pull_request_target`.
- **Concurrency:** Concurrency groups cancel outdated runs on the same branch successfully.

## 5. Conclusions & Blockers

- **API Blocker:** As of the current audit, ruleset 13643213 is disabled, meaning there is **no stable required status demonstrably blocking merges on failure**.
- **Actionable:** Enable the required checks ruleset on `main` branch to require the `pr-gate-complete` context for merge protection.
