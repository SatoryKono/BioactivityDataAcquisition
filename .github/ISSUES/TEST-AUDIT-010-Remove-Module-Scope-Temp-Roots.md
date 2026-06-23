---
title: "[TEST-AUDIT-010] Remove module-scope temp roots from unit test import paths"
github_issue: 5495
labels: technical-debt
assignees: []
---

## Context

The 2026-06-22 audit found that several `tests/unit/**` files create real
temporary directories at module import time through `Path(tempfile.mkdtemp(...))`.

## Problem

A targeted scan found 22 unit test files with module-scope temp roots.
Representative examples:

- `tests/unit/composition/factories/pipeline/test_pipeline_factory.py`
- `tests/unit/infrastructure/factories/test_storage_adapter.py`
- `tests/unit/infrastructure/adapters/test_cached_bronze_support.py`
- `tests/unit/composition/bootstrap/test_checkpoint_bootstrap.py`
- `tests/unit/composition/bootstrap/test_storage_bootstrap.py`

These tests create filesystem state before pytest fixtures can manage lifecycle
and before markers/lanes can isolate side effects.

## Acceptance Criteria

- [ ] No `tests/unit/**/test_*.py` file creates temp directories at import time.
- [ ] Filesystem-dependent unit tests use pytest-managed fixtures.
- [ ] Pure unit lanes remain deterministic under xdist.
- [ ] Repo-backed or integration semantics are explicitly marked where real filesystem behavior is intentional.
- [ ] A guard prevents recurrence.

