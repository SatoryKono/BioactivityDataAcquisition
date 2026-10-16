# Architecture-full Gate Unblock Issue Pack — 2026-08-25

**Evidence:** verify-architecture full (Windows `.venv-win`), 2026-08-25.

**Command:** `pytest tests/architecture/ -m "not slow and not benchmark and not memory"`

**Result:** 92 failed / 4318 passed / 74 skipped / 4484, exit 1, ~692 s.

**Related program epic (do not duplicate):** #9617

**Policy:** debt budgets may only stay flat or decrease (`AGENTS.md`).

## Issue codes — published

| Code | Pri | Issue | URL |
|---|---|---:|---|
| ARCH-VG-00 | meta/P0 | #9639 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9639 |
| ARCH-VG-01 | P0 | #9640 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9640 |
| ARCH-VG-02 | P0 | #9642 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9642 |
| ARCH-VG-03 | P1 | #9641 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9641 |
| ARCH-VG-04 | P1 | #9644 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9644 |
| ARCH-VG-05 | P2 | #9643 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9643 |

Publish record: `reports/quality/architecture-verify-full-2026-08-25-issue-publish.json`

## Explicit non-duplicates

- #9624 — ADR matrix / scorecard integral coherence
- #9622 — mixin aggregate reassembly
- #9626 — planned private-import shrink below 19
- #9620 — collapse remaining `*_api` facades
