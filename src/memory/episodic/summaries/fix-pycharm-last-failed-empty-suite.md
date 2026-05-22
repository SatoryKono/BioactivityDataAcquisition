---
id: fix-pycharm-last-failed-empty-suite
title: Fix PyCharm last-failed empty e2e suite exit
task_id: fix-pycharm-last-failed-empty-suite
created_at: '2026-05-22T10:02:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Normalized pytest --last-failed empty-suite runs to exit 0 when tests were
  collected before deselection; added unit coverage and verified tests/e2e --last-failed
  returns success.
---

# Episodic summary

## Task

- Title: Fix PyCharm last-failed empty e2e suite exit

## Outcome

- Normalized pytest --last-failed empty-suite runs to exit 0 when tests were collected before deselection; added unit coverage and verified tests/e2e --last-failed returns success.

## Lessons learned

- Replace with durable follow-up if needed
