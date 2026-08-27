# Requirements traceability audit

Cycle-run: `20260827T1050Z-req-new2-11a4ba92`  
Prompt: `prompt.audit.project.new2.requirements-trace`

## Executive summary

Two PROVEN gaps: catalog index lagged the CSV for `REQ-DASH-004`, and tests cited invented `REQ-*` IDs. Both paid down without new IDs or debt-budget increases.

## Surface

- CSV: 172 unique rows, no duplicates
- REQUIREMENTS.md: 172 active, 151 MUST (v1.12.6)
- Tests: catalog-only `REQ-*-NNN` citations (ratchet in `test_requirements_traceability_catalog.py`)

## Top gaps (paid)

1. AUD-REQ-001 / REQ-DASH-004 / P1 — index vs CSV
2. AUD-REQ-002 / GAP / P2 — invented test IDs
