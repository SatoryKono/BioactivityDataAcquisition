---
id: fix-mutation-report-gate
title: Harden mutation report generation gate
task_id: fix-mutation-report-gate
created_at: '2026-05-21T08:41:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- .github/workflows/mutation-testing.yml
summary: 'Removed mutmut report-step failure masking so report generation still runs
  with if: always() but now fails the job when mutmut results or mutmut html break.'
---

# Episodic summary

## Task

- Title: Harden mutation report generation gate

## Outcome

- Removed mutmut report-step failure masking so report generation still runs with if: always() but now fails the job when mutmut results or mutmut html break.

## Lessons learned

- Replace with durable follow-up if needed
