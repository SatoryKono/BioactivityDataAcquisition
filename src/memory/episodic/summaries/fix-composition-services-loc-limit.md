---
id: fix-composition-services-loc-limit
title: Fix composition services LOC limit
task_id: fix-composition-services-loc-limit
created_at: '2026-05-26T10:28:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/_services.py
- tests/architecture/test_code_metrics.py
summary: Reduced src/bioetl/composition/_services.py from 351 to 350 lines by removing
  a non-semantic blank line between bootstrap constants and mapping; validated targeted
  WSL and Windows composition file-size architecture checks.
---

# Episodic summary

## Task

- Title: Fix composition services LOC limit

## Outcome

- Reduced src/bioetl/composition/_services.py from 351 to 350 lines by removing a non-semantic blank line between bootstrap constants and mapping; validated targeted WSL and Windows composition file-size architecture checks.

## Lessons learned

- Replace with durable follow-up if needed
