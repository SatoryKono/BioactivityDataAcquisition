# Iteration 1 — hierarchy and inventory

## Evidence

- `git ls-files configs` returned 256 tracked config assets.
- Canonical hierarchy counts: `configs/base` 5, `configs/providers` 7,
  `configs/entities` 27, `configs/composites` 7 (5 pipeline configs plus 2
  field-group policies).
- Provider names match non-composite entity provider directories.
- Five `configs/composites/*.yaml` pipeline names match five
  `configs/entities/composite/*.yaml` contracts.
- Legacy runtime roots `configs/pipelines`, `configs/schemas`,
  `configs/sources`, `configs/filters`, and `configs/hash_policy` are absent.

## Result

PASS. Hierarchy is not inverted and canonical owners are unambiguous.
Delta: unchanged. Debt effect: unchanged.
