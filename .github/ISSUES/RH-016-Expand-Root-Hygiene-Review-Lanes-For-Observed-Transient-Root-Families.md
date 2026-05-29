# Expand Root Hygiene Review Lanes For Observed Transient Root Families

**Status**: active
**Priority**: P2
**Labels**: `governance`, `tooling`, `cleanup`, `priority:medium`
**Last audited**: 2026-05-19

## Problem

The current root-hygiene review registry already tracks several historical
reintroduction lanes, but the newly observed transient root families are still
mostly handled only at the final hard-fail audit stage.

Observed live examples:

- `temp_analyze_conflicting.py`
- `temp_get_hash.py`
- `test_output.txt`
- root `artifacts/` output routing

This means the repo has a good red-line failure (`audit_root_cleanliness.py`),
but weaker intermediate guidance about:

- canonical owner paths for these families
- expected remediation action when they reappear
- whether a path is a maintained helper, archive candidate, or disposable
  transient output

## Evidence

- `configs/quality/root_hygiene_review_registry.yaml`
- `scripts/ops/support/repo/cleanup_repository.py`
- `scripts/engineering/repo/audit_root_cleanliness.py`
- `docs/plans/root-hygiene-review-lane-automation-2026-04-29.md`

## Proposed Solution

Extend root-hygiene review metadata so that the next reintroduction of these
families is classified earlier and more specifically than a generic root-audit
failure.

This can be done by:

- adding concrete candidates or candidate-family notes to
  `configs/quality/root_hygiene_review_registry.yaml`
- documenting canonical destination classes for temp helper scripts, root text
  outputs, and non-approved artifact directories
- optionally teaching cleanup/report tooling to surface these families as
  `REVIEW_REQUIRED` guidance before they become normalized drift

## Scope

- add review-lane coverage for root `temp_*.py` helper families
- add review-lane coverage for root diagnostic/output text families such as
  `*_output.txt`
- add review-lane coverage for unapproved root artifact directories when they
  are referenced by config/tests
- record the expected canonical owner class for each family
- keep the registry aligned with existing root audit policy rather than
  creating a second competing policy

## Non-Goals

- do not relax root audit failures into warnings
- do not add a blanket allowlist for temp root files
- do not make cleanup tooling delete tracked review-required paths

## Acceptance Criteria

- the root-hygiene review registry includes the observed transient root
  families or an equivalent explicit family-level rule
- each family has a documented remediation action and canonical destination
  class
- the review registry remains consistent with root audit policy and existing
  tests

## Validation

```bash
./.venv/bin/python -m pytest -q \
  tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py \
  tests/architecture/test_root_hygiene_review_registry.py \
  tests/unit/scripts/repo/test_cleanup_repository.py
```

## Risks

- duplicating logic between registry and root audit can create drift if the
  family rules are not kept minimal
- overfitting the registry to one branch snapshot would make the rules noisy

## Related

- follows `RH-014`
- follows `RH-015`
