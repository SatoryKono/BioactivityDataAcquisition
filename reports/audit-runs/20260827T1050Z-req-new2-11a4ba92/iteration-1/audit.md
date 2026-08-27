# Iteration 1 — requirements traceability

Cycle-run: `20260827T1050Z-req-new2-11a4ba92`

## A Inventory

CSV on `origin/main` after catch-up: **172** unique rows, no duplicates (151 MUST / 16 MUST NOT / 4 SHOULD / 1 MAY). `REQUIREMENTS.md` still claimed **171** / 150 MUST. Markdown family IDs in the index; row IDs live in the CSV.

## B Trace

| REQ | Path | Result |
| --- | --- | --- |
| REQ-DASH-004 | `DASHBOARD_REQUIREMENTS.md:160` → scalar-density tests | CSV row existed; index/snapshot stale; executable_surface wrong |
| REQ-LOAD-002 | `tests/architecture/test_force_full_scan_publication.py` | traced |
| 134/172 CSV IDs | not string-cited in tests | NOT treated as missing coverage (file-count ban) |

## C Drift

Invented test IDs (not in CSV): `REQ-ARCH-008+`, `REQ-CONF-*`, `REQ-PERF-*`, `REQ-DOC-010`, `REQ-DETERM-001`, `REQ-DQ-010/020/030`. No invented IDs added to the CSV.

## D Issues

- #9756 `[req][REQ-DASH-004][P1]`
- #9757 `[req][GAP][P2]`

## E Fix

- REQUIREMENTS.md v1.12.6, 172 / 151 MUST, observability 43
- crosswalk.md snapshot 172 / DASH-001..004
- CSV `REQ-DASH-004` executable_surface → scalar-density tests
- Remap invented test citations; catalog ratchet `test_requirements_traceability_catalog.py`

## F Validate

`pytest tests/architecture/test_requirements_traceability_catalog.py` + presentation routing + remapped architecture tests: **26 passed**. Debt budgets unchanged.
