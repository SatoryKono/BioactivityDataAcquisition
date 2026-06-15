---
id: fix-dq-report-gold-provenance-path
title: Fix gold DQ report path generation for provenance integration test
task_id: fix-dq-report-gold-provenance-path
created_at: '2026-06-15T11:34:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Investigated the reported gold DQ provenance-path failure. The targeted integration
  test and the full test_dq_report_integration.py module both pass on WSL and Windows
  .venv-win, so no code change was needed on the current checkout. The prior failure
  appears stale or caused by external suite-order leakage outside this module.
---

# Episodic summary

## Task

- Title: Fix gold DQ report path generation for provenance integration test

## Outcome

- Investigated the reported gold DQ provenance-path failure. The targeted integration test and the full test_dq_report_integration.py module both pass on WSL and Windows .venv-win, so no code change was needed on the current checkout. The prior failure appears stale or caused by external suite-order leakage outside this module.

## Lessons learned

- Replace with durable follow-up if needed
