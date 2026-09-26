# Wave F closeout (C2) — #7695 + #8032

## Decision

**Close #8032 and #7695** after publishing Wave F findings and fixing application
unit lane purity residual (WF-01).

## Why close without new CR path-cluster issues

1. Residual CLI leaves S12–S15 failed with product error
   `Review failed: All files are ignored` (same class as Wave E / #8031).
2. Zero major/critical findings from Wave F CLI residual.
3. Architecture honesty gates are the accepted alternate residual path
   (`test_application_unit_lane_purity`, domain unit purity, assert density,
   VCR policies, closeout ratchet honesty).
4. One gate residual (concrete infrastructure imports in application unit tests)
   fixed in closeout branch; no debt-budget growth.

## Done

- [x] `FINDINGS_wave_F.md` under `reports/quality/coderabbit/20260806/`
- [x] WF-01 purity fix + infrastructure unit placement for PK helpers
- [x] Issue comments + close #8032, #7695

## Not in scope for Wave F

- Product typing budget (`Any`) / files_ge_250_loc residual snapshot
- Wave E docs/grafana residual (#7694/#8031) — separate stream
- Implementing open GRA/UX epics
