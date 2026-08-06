# Wave E closeout (C1) — #7694 + #8031

## Decision

**Close #8031 and #7694** after publishing Wave E findings and fixing ADR-053
scenes parity ledger SSOT drift.

## Why close without new CR path-cluster issues

1. Residual CLI leaves S17–S19 all failed with product error
   `Review failed: All files are ignored` (evidence in `/tmp/bioetl-cr-artifacts/20260805/`).
2. Zero major/critical CR findings to publish.
3. Open Grafana operator work is already tracked under GRA/UX issues (#8047–#8050,
   #7639, #6806, #6988, …) — de-duped, not re-filed.
4. Repo contract residual (scenes parity ledger) fixed in closeout PR.

## Done

- [x] FINDINGS_wave_E.md tracked under `reports/quality/coderabbit/20260806/`
- [x] scenes-parity-ledger.json regenerated
- [x] Issue comments + close #8031, #7694

## Not in scope for Wave E

- Implementing open Grafana UX epics (#8050 family)
- Docker monitoring stack (ADR-010 optional)
- Wave F (#7695/#8032) — separate stream
