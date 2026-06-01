---
id: quarantine-accounting-plan
title: Plan quarantine accounting changes
task_id: quarantine-accounting-plan
created_at: '2026-06-01T18:45:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/processed_records_table.py
summary: 'Reviewed and improved the quarantine accounting plan. Key decision: keep
  physical quarantine storage separate from Processed Records accounting categories,
  avoid double counting FILTERED_OUT_SILVER as silver_quarantined, and prioritize
  exact-run ledger consistency plus tests/docs.'
---

# Episodic summary

## Task

- Title: Plan quarantine accounting changes

## Outcome

- Reviewed and improved the quarantine accounting plan. Key decision: keep physical quarantine storage separate from Processed Records accounting categories, avoid double counting FILTERED_OUT_SILVER as silver_quarantined, and prioritize exact-run ledger consistency plus tests/docs.

## Lessons learned

- Replace with durable follow-up if needed
