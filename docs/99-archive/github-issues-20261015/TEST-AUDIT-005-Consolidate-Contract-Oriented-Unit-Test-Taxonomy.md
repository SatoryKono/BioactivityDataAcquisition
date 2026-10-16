---
title: "[TEST-AUDIT] Consolidate contract-oriented unit test taxonomy"
github_issue: 5430
labels: enhancement, maintainability, technical-debt
assignees: []
---

## Context

The current tree contains both `tests/unit/contract/` and `tests/unit/contracts/`.
The canonical contracts lane already targets `tests/contract/` plus
`tests/unit/contracts/`, while `tests/unit/contract/` currently contains a lone
helper-style test module.

## Problem

- Two near-identical directory names create navigation drift.
- Only one of them is wired into the canonical contracts lane.
- The remaining singular path looks accidental even if its current content is
  still useful.

## Evidence

- `configs/quality/test_matrix.yaml`
- `tests/unit/contract/test_chembl_contract_helper.py`
- `tests/unit/contracts/`

## Proposed Solution

1. Decide one canonical pluralized unit-contract surface.
2. Move or rename the singular-path content into the canonical location.
3. Remove residual naming drift from lane docs and contributor expectations.

## Acceptance Criteria

- [ ] Only one canonical unit-contract directory naming pattern remains
- [ ] Contracts lane paths and filesystem layout agree
- [ ] No helper or test is orphaned by the rename/move

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/pytest \
  tests/unit/contracts/ tests/contract/ -p no:xdist -q
rg -n "tests/unit/contract|tests/unit/contracts" \
  configs/quality/test_matrix.yaml tests
```

## Risks

- Path churn can affect shard inventories, docs, and ad hoc scripts.
