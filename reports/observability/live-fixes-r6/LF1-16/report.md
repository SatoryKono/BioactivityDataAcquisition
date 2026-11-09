# LF1-16 Incident Dashboard Verification

## 1. Context & Setup
- Source/Deploy SHA: `9b33adf0174a97ec88a7b95942e6a78eaf40cf1a`
- Time: `2026-11-08T19:19:00Z`
- Target Panels: 2101 (Status), 9451 (Domains), 9463 (Duration)

## 2. Matrix Testing
- UUID A: `f002-abc`
- UUID B: `f003-abc`
- Unresolved: `-` (Empty stage fallback checked)

**Status & Findings**
- Matrix execution blocked by `blocked_backend_unavailable` (backend server not up) and `blocked_unavailable` due to sandbox limitations where docker backend is inaccessible.

## 3. Results (Checklist)
- [ ] Matrix B/C on two UUIDs and the negative case: `NOT_VERIFIABLE`. The backend was unavailable and the selected-run cases were not executed.
- [ ] Panel data aligned with API/frame: `NOT_VERIFIABLE`. The blocked audit did not produce the responses or frames needed for comparison.
- [x] Result attached as report with exact source/deploy SHA, UTC time, parameters, and expected/actual verification references.

The JSON records the blocked audit. Its semantic gate is `fail`. A top-level `ok` on an optional result describes its non-blocking disposition. Treat rows classified `blocked_backend_unavailable` or `blocked_unavailable` as unavailable when reusing this report. Selected-run frames and deployed revision still require evidence from a live run.
