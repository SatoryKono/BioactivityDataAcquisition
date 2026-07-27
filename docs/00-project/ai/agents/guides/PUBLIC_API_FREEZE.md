# Public API freeze (TD-R-07 / #6683)

Last reviewed: 2026-07-27

Permanent public product seams are **not** dead code.

## Freeze ceilings (shrink-only)

- Retained public entrypoints: **≤ 12**
- Export facades: **≤ 4**
- Twin pairs / transition burden: **0**

## Adding a public seam

1. Architecture review on the PR.
2. Update `configs/quality/compatibility_facade_inventory.yaml`.
3. Refresh `reports/quality/compatibility-importer-census.json`.
4. Prefer owner modules over package-root convenience imports in first-party code.

## Tests

- `tests/architecture/test_public_api_freeze_counts.py`
- Existing public facade inventory / debt scorecard KPIs
