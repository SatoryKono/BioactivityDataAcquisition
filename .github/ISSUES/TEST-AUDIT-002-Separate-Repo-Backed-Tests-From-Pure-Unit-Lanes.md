---
title: "[TEST-AUDIT] Separate repo-backed tests from canonical pure-unit lanes"
github_issue: 5424
labels: enhancement, architecture, technical-debt
assignees: []
---

## Context

The repository already acknowledges a `repo-backed-unit` lane, but repo-backed
tests still live inside the broad `tests/unit/**` tree and rely on an autouse
restore hook that rewrites `src/bioetl/composition/bootstrap/runtime/pipeline.py`
after marked tests.

## Problem

- The mental model of "unit" is overloaded: pure unit tests and
  repository-file-backed contract checks share the same broad tree.
- The restore hook proves these tests can mutate production-file surfaces.
- This is controlled debt, but it still blurs the canonical `unit-fast` and
  `unit-parallel-safe` boundaries.

## Evidence

- `configs/quality/test_matrix.yaml`
- `tests/conftest.py`
- repo-backed markers across `tests/unit/**`

## Proposed Solution

1. Define one canonical home for repo-backed tests.
2. Move marked tests into that home or enforce a naming/path convention that is
   impossible to confuse with pure-unit coverage.
3. Keep `unit-fast` and `unit-parallel-safe` as the canonical pure-unit lanes.
4. Document the ownership and mutation rules for repo-backed tests.

## Acceptance Criteria

- [ ] Repo-backed tests have one explicit canonical subtree or path convention
- [ ] Lane documentation distinguishes pure-unit from repo-backed behavior
- [ ] Restore-hook rationale is documented against the repo-backed lane
- [ ] `unit-fast` / `unit-parallel-safe` semantics remain unchanged

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/unit/ -m "repo_backed" -p no:xdist -q
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/unit/ -m "not repo_backed and not slow and not benchmark and not memory" \
  -p no:xdist -q
```

## Risks

- Broad moves can break shard inventories or local muscle memory.
- The fix must not reclassify pure-unit tests as repo-backed by convenience.
