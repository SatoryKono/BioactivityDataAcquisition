# Shadow Window N1 Status Report

**T (Observation start):** 2026-11-02T07:10:42Z
**Earliest possible completion:** T + 48 wall-clock hours (two full days; not calendar-date hops).
**Protocol source of truth:** `window_protocol` / `next_window` in `reports/governance/n1-shadow-window/ledger.json` (same 48-hour P0 span; independent review is not an acceptance gate; durable archive still needs the 90-day age flag before `require-accepted`).

**Branch Info:**
- `main` SHA: acc8d0f344a048f8d659671f59da2de279a20616 (Base)
- Current Branch: fix/shadow-comparison-nightly-evidence
- HEAD SHA: *(To be generated upon commit)*

**Configuration & Run Info:**
- Baseline Configuration: `daily-deterministic-plus-existing-weekly-security`
- Baseline SHA: `acc8d0f344a048f8d659671f59da2de279a20616`
- Candidate Runs/Attempts: *(Pending gathering in CI environment)*

**Archive Path & Availability:**
- Append-only archive path: `reports/governance/n1-shadow-window`
- Unacceptable history index path: `reports/governance/n1-shadow-window/unacceptable/index.json`
- Access: Available in this repository tree.

**Blocker & Refusal:**
- Command: `uv run python -m scripts.engineering.ci.nightly_shadow_archive archive --repository SatoryKono/BioactivityDataAcquisition --output reports/governance/n1-shadow-window --limit 100`
- Exit Status: 1
- Error: `error: [Errno 2] No such file or directory: 'gh'`

**Continuation Owner:**
- Coordinator / Action Runner scheduled to gather results during the 48 hour span using an environment with GitHub CLI authenticated.
