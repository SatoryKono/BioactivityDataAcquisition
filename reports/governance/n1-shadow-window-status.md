# Shadow Window N1 Status Report

**T (Observation start):** ещё не установлен (Not yet established, awaiting first valid pair on main).
**Earliest possible completion:** T + 48 wall-clock hours (two full days; not calendar-date hops).
**Protocol source of truth:** `window_protocol` / `next_window` in `reports/governance/n1-shadow-window/ledger.json` (same 48-hour P0 span; independent review is not an acceptance gate; durable archive still needs the 90-day age flag before `require-accepted`).

**Branch Info:**
- `main` SHA: 2f96956bb2fba6d102703847b6bd08518c6edd65 (Base)
- Current Branch: ci/nightly-shadow-comparison
- HEAD SHA: *(To be generated upon commit)*

**Configuration & Run Info:**
- Baseline Configuration: `daily-deterministic-plus-existing-weekly-security`
- Baseline SHA: `ce050a180ffea36a2ff1400e3d66c4ebcc3bcaaf`
- Candidate Runs/Attempts: *(Pending gathering in CI environment)*

**Archive Path & Availability:**
- Append-only archive path: `reports/governance/n1-shadow-window`
- Unacceptable history index path: `reports/governance/n1-shadow-window/unacceptable/index.json`
- Access: Available in this repository tree.

**Continuation Owner:**
- Coordinator / Action Runner scheduled to gather results during the 48 hour span.
