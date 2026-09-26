# Requirements traceability cycle 1

**run_id:** 2026-08-28T0634Z-req-new2-61fa446
**SHA:** 61fa4461de
**BASE:** main | **WORK_BRANCH:** fix/req-trace-cycle-new2-61fa446
**SCOPE:** docs/01-requirements/ tests/ src/bioetl/
**MODE:** full | **N:** 10 | **Iteration:** 1/10 (audit-only, no mutations yet)
**ALLOW_*:** true

## Preflight
- SHA 61fa446, branch main, remote origin git@github.com:SatoryKono/BioactivityDataAcquisition.git
- CSV 172 rows uniq 172 dups 0 status 166 confirmed 6 updated modality 151 MUST 16 MUST NOT 4 SHOULD 1 MAY
- Open issues 17 (P0/P1 security/governance/arch), open PRs 2

## Inventory (Phase A)
- MD vs CSV: MD mentions 3 REQ-* (REQ-DASH-001/004, REQ-DQ-002) delegating to CSV - OK per design
- CSV uniq 172 - canonical

## Trace (Phase B)
- tests/ covers 40/172 (23.3%), src/bioetl/ covers 19/172 (11%), union 49/172 (28.5%)
- Untraced in tests: 132 (76.7%) - 26 concrete (bindable) + 106 generic orphan
- Orphan generic executable_surface: 137/172 (79.6%) - no file/command path

## Drift (Phase C)
- Invented in docs: 12 (REQ-ARCH-030/031/040/041 + REQ-VAL-001..008) - RULES.md + ADR-033
- Invented in src: 9 (REQ-ARCH-011/012/013/030, REQ-AUDIT-001/002, REQ-CONF-001, REQ-ERR-015, REQ-OBS-010)
- Invented in tests: 0 - clean

## Findings (PROVEN)
- REQ-TRACE-001 P2 orphan generic (REQ-ARCH-004 anchor) - 137 generic
- REQ-TRACE-002 P2 untraced concrete (REQ-GOV-001 anchor) - 26 concrete not bound
- REQ-TRACE-003 P1 drift invented (REQ-ARCH-030 anchor) - 12 docs + 9 src invented

## Plan (3 waves, flat debt)
Wave1: CSV sync for invented (or remove markers)
Wave2: Tag existing tests for 26 concrete untraced
Wave3: Harden top 20 generic orphan with concrete paths

## Next
Issues phase D requires approve to create up to 5 per iteration (MAX_ISSUES=5). This iteration produced 0 issues (plan owns).

## Issues created (iter1)
- #9803 [req][GAP][P1] drift (REQ-TRACE-003 GAP)
- #9805 [req][REQ-GOV-001][P2] untraced concrete 26
- #9806 [req][GAP][P2] orphan generic 137

Early-stop: new_issues 3 >0 -> NO stop, need fix iteration 2 (MAX_ISSUES 5 not exceeded).


## Iteration 1 Fix

Src invented cleanup attempted then reverted to match origin/main bulk CSV 172->192. Closed #9803 P1. Updated #9805/#9806 for 192 baseline. Next: Waves 2+3.


## Iteration 2

26 bindings (tests 40->66, untraced 132->106), crosswalk 20 hardened (orphan 136->116). Branch ahead origin by 1 commit (05-github-policy sync). Ready for git commit + push.
