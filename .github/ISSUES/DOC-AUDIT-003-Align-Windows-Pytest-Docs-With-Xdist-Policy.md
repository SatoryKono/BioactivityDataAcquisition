---
title: "docs(testing): align mixed Windows + WSL pytest examples with the current xdist worker cap"
labels: documentation, enhancement
assignees: []
---

## Context

The 2026-06-19 documentation audit found that onboarding and testing docs still
recommend `-n 4` for mixed Windows + WSL checkouts, while the current runtime
policy caps Windows xdist workers to `1`.

## Problem

Current docs still recommend commands like:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 4 --lf
```

But the audited runtime/test policy now explicitly guards Windows parallelism:

- wrapper defaults return `1` on Windows;
- `run_pytest.ps1` sets `PYTEST_XDIST_AUTO_NUM_WORKERS` to `1` unless overridden;
- `tests/conftest.py` caps Windows xdist workers even when tests bypass the repo wrappers.

This drift can send Windows users into avoidable socket/buffer failures and
conflicts with the current tested policy.

## Evidence

- `README.md:198`
- `docs/03-guides/getting-started.md:67`
- `docs/03-guides/quick-start.md:53`
- `docs/03-guides/testing.md:698`
- `docs/03-guides/github-local-workflow.md:45`
- `scripts/engineering/dev/run_tests.py:106-112`
- `scripts/engineering/dev/run_pytest.ps1:355-361`
- `tests/conftest.py:339-352`
- `tests/unit/tools/test_pytest_last_failed_policy.py`
- `tests/unit/scripts/test_dev_run_tests_windows_parallel_guard.py`

## Proposed Solution

1. Replace stale Windows `-n 4` examples with wrapper-default usage or explicit
   `-n 1`.
2. Mention `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS` as the sanctioned override.
3. Keep Linux/WSL guidance separate where `auto` or higher parallelism remains
   acceptable.
4. Re-scan mixed-checkout docs so the same stale example is removed
   repo-wide.

## Acceptance Criteria

- [ ] Windows mixed-checkout docs no longer recommend `-n 4` as the default local path.
- [ ] At least one canonical guide explains the Windows worker-cap policy and override env var.
- [ ] Linux/WSL examples remain valid and clearly separated from Windows behavior.
- [ ] Repo search confirms the stale Windows example is gone from active docs.

## Validation

```bash
rg -n -- "\\.\\\\scripts\\\\engineering\\\\dev\\\\run_pytest\\.ps1 tests\\\\ --timeout=120 -n 4 --lf|bash scripts/engineering/dev/run_pytest\\.sh tests/ --timeout=120 -n 4 --lf" \
  README.md docs/03-guides docs/05-operations
rg -n "BIOETL_PYTEST_WINDOWS_XDIST_WORKERS|_default_parallel_workers|_configure_windows_xdist" \
  scripts/engineering/dev/run_tests.py scripts/engineering/dev/run_pytest.ps1 tests/conftest.py
```

## Non-Goals

- changing the Windows test policy itself
- reworking pytest wrappers
- addressing unrelated test-suite failures

