# Root Hygiene Cleanup Hardening 2026-04-29

## Scope

This note records the bounded implementation step that hardened
`scripts/ops/support/repo/cleanup_repository.py` against the published cleanup
policy without widening deletion into governed or retention-sensitive surfaces.

## Implemented

- Kept cleanup path-scoped and blocked-zone aware via
  `is_within_blocked_cleanup_zone(...)`.
- Extended exact local directory-family discovery to include:
  - `.ipynb_checkpoints/`
  - `*.egg-info/`
- Extended exact local file-family discovery to include:
  - `*.log`
  - `*.tmp`
  - `full_log.txt`
  - `final_report*.txt`
  - `project_rules_failures.txt`
- Preserved the existing exact local families for:
  - compiled artifacts (`*.pyc`, `*.pyo`)
  - coverage artifacts (`.coverage*`, `coverage.xml`)
  - local cache/build roots (`.pytest_cache/`, `.mypy_cache/`, `build/`, `dist/`, `htmlcov/`, etc.)

## Explicit Non-Goals

- No broad cleanup over tracked project tree.
- No deletion inside blocked cleanup zones such as `reports/` and `data/`.
- No automatic cleanup for generic `*report*.txt` across the repository.

The generic report-like pattern remains intentionally outside auto-delete
semantics because it has a higher false-positive risk than the exact filenames
and prefix-patterns above.

## Verification

Validated by:

- `tests/unit/scripts/repo/test_cleanup_repository.py`
- governance slice:
  - `tests/architecture/test_scripts_catalog_governance.py`
  - `tests/architecture/test_scripts_inventory_discovery.py`
  - `tests/architecture/test_scripts_lifecycle_registry.py`
  - `tests/architecture/test_scripts_lifecycle_fast_guard.py`
  - `tests/architecture/test_scripts_deprecation_backlog.py`
  - `tests/architecture/test_lint_terminology_script.py`

## Follow-Up

The next safe step is not broader deletion. It is review-lane automation for
`REVIEW_REQUIRED` root surfaces so evidence collection (`git ls-files`,
`git log`, `cmp`, `rg`) becomes deterministic and reportable before any
path-specific removal decision.
