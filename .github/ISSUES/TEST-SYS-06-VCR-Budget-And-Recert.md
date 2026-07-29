---
title: "[P1][testing] TEST-SYS-06: VCR size/age budget + recert workflow flag truth"
labels: P1, testing, performance, http, governance, ci, quality
assignees: []
github_issue: 7028
---

## Context

VCR is the dominant fixture weight (~**139 MB** / **402** cassettes vs bronze
~1.7 MB). Ledger forbids age-only deletes (correct for reproducibility). Matrix
flag `cassette_metadata_backfill_workflow_present: false` while backfill tooling
exists elsewhere.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §2.4, F2/F4, P1-4  
**Epic:** TEST-SYS-00

## Problem

Unbounded cassette growth slows clone/CI; recert path is ops-friction without
truthful workflow flags.

## Scope / modules

- `tests/fixtures/vcr/**`
- `configs/quality/fixture_governance_ledger.yaml`
- `configs/quality/test_matrix.yaml` (fixture governance flags)
- VCR skill / record docs: `.codex/skills/vcr-record/`
- Provider cassette directories (chembl, pubchem, openalex, …)

## Acceptance Criteria

- [ ] Define per-provider cassette **size/count budget** (ratchet: budgets may only stay flat or decrease)
- [ ] Align matrix flags with real workflows (`cassette_metadata_backfill_workflow_present` truth)
- [ ] Staleness policy remains ≤ ledger max age with **recert**, not silent delete
- [ ] Document operator recert path; no secret leakage in cassettes
- [ ] Governance tests green

## Constraints

- Do **not** age-only mass-delete cassettes
- Prefer provider-scoped jobs + cache over global parallel VCR writers

## Related

- TEST-SYS-01 (bronze exact-replay — complementary medallion surface)
