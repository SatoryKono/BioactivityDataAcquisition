# Tech Debt Audit 2026-07-03 Issue Pack (Wave 3)

This pack converts the refreshed `2026-07-03` technical-debt audit on current
`main` into a publish-ready GitHub issue set. It follows the closed Wave 1
(`TDX-AUDIT-001`–`007`) and Wave 2 (`TDX-AUDIT-008`–`011`) closeouts and
targets residual debt that governance gates still allow but the live artifacts
continue to report.

Prior pack: `.github/ISSUES/TECH-DEBT-AUDIT-2026-07-01-ISSUE-PACK.md`

## Decision Summary

| Finding theme | Current repo actuality | Action |
| --- | --- | --- |
| Debt governance gates | `31/31` pass, integral score `8.54` | Do not create issue |
| Layering / ADR enforcement | `0` layer violations; `48/48` ADRs enforced | Do not create issue |
| Contract / config drift | `27/27` registry valid; `0` inconsistent parameters | Do not create issue |
| Bronze / VCR gaps | `bronze_fixture_gaps.yaml` empty; `198` cassettes, `0` review-required | Do not create issue |
| Hotspot-family duplication (5 targets) | `0` duplicate clusters | Do not create issue |
| Full-app duplication outside hotspot ratchet | `57` clusters (`48` adapters, `9` pipelines) | Create issue |
| Partial-coverage replay tail | `855` partially covered / `2211` modules | Create issue |
| Zero-reference supporting scripts | `50` scripts with `reference_count = 0` | Create issue |
| Lazy export public surfaces | `43` classified module-level `__getattr__` facades | Create issue |
| Hotspot families at budget ceiling | `6` `budget_review_notes`; control-plane `13/16` LOC≥250, fan-in `4/4` | Create issue |
| Bootstrap/runtime composition complexity | `48` modules under `composition/bootstrap/runtime/`; dup `0` but high wiring surface | Create issue |
| Duplication baseline artifact hygiene | `hotspot-duplication-baseline.*` whitelisted for git but not yet release-authoritative everywhere | Create issue |

## Publish-Ready Set

### Wave 3 — enforcement and residual structural burn-down (closed)

Closeout: `reports/quality/tech-debt-issues-5866-5872-closeout.json`

1. `TDX-AUDIT-012` Add full-app duplication ratchet to scorecard and architecture CI [#5866](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5866) — closed
2. `TDX-AUDIT-013` Burn down infrastructure adapter duplication clusters from the 48-cluster baseline [#5867](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5867) — closed
3. `TDX-AUDIT-014` Burn down application pipeline transformer duplication from the 9-cluster baseline [#5868](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5868) — closed
4. `TDX-AUDIT-015` Ratchet replay-sensitive partial-coverage module floors beyond zero uncovered [#5869](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5869) — closed
5. `TDX-AUDIT-016` Enforce zero-reference supporting-script owner-or-removal governance in CI [#5870](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5870) — closed
6. `TDX-AUDIT-017` Migrate first-party lazy-export consumers to canonical import owners [#5871](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5871) — closed
7. `TDX-AUDIT-018` Consolidate composition bootstrap runtime composite builder bundles [#5872](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5872) — closed

## Recommended Execution Order

### Phase 2 — Isolation (enforcement first)

1. `TDX-AUDIT-012`

### Phase 3 — Removal (largest duplication leverage)

2. `TDX-AUDIT-013`
3. `TDX-AUDIT-014`

### Phase 3 — Removal (compatibility and composition)

4. `TDX-AUDIT-017`
5. `TDX-AUDIT-018`

### Phase 4 — Enforcement (tails and hygiene)

6. `TDX-AUDIT-015`
7. `TDX-AUDIT-016`

## Why These Seven

Wave 1 and Wave 2 closed governance packaging and high-risk determinism/hotspot
owners, but live artifacts on `2026-07-03` still show:

- full-app duplication that is **not** covered by the five hotspot-family zero
  budgets;
- a broad partial-coverage tail (`855` modules) that is green only on uncovered
  count, not replay depth;
- fifty supporting scripts with zero tracked references;
- forty-three sanctioned lazy-export surfaces still depending on import
  indirection;
- composition bootstrap/runtime wiring that remains change-sensitive even when
  duplicate clusters are zero.

Wave 3 turns those residuals into explicit owners with flat-or-decreasing
ratchets. No scorecard budget may grow.

## Evidence Anchors

- `reports/quality/total-tech-debt-audit-main-2026-07-01.md` (refreshed 2026-07-03 session)
- `reports/quality/debt-governance-gates.json`
- `reports/quality/full-app-duplication-baseline.json`
- `reports/quality/hotspot-duplication-baseline.json`
- `reports/quality/hotspot-family-baseline.json`
- `reports/quality/module-coverage-inventory.json`
- `reports/quality/compatibility-importer-census.json`
- `tests/architecture/test_lazy_export_public_api_inventory.py`
- `configs/quality/scripts_inventory_manifest.json`
