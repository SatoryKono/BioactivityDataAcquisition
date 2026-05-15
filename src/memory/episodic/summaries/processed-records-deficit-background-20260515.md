---
id: processed-records-deficit-background-20260515
title: Mark Processed Records silver and gold deficits with red row background
task_id: processed-records-deficit-background-20260515
created_at: '2026-05-15T11:37:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added Processed Records row_status deficit marker. Silver rows get silver_deficit
  when Silver accounted sum is below bronze; Gold rows get gold_deficit when Gold
  accounted sum is below silver valid. Dashboard JSON uses hidden-width row_status
  with color-background applyToRow. Updated tests/docs and validated live endpoint.
---

# Episodic summary

## Task

- Title: Mark Processed Records silver and gold deficits with red row background

## Outcome

- Added Processed Records row_status deficit marker. Silver rows get silver_deficit when Silver accounted sum is below bronze; Gold rows get gold_deficit when Gold accounted sum is below silver valid. Dashboard JSON uses hidden-width row_status with color-background applyToRow. Updated tests/docs and validated live endpoint.

## Lessons learned

- Replace with durable follow-up if needed
