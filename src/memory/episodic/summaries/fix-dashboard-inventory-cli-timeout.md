---
id: fix-dashboard-inventory-cli-timeout
title: Fix dashboard inventory CLI help timeout
task_id: fix-dashboard-inventory-cli-timeout
created_at: '2026-05-25T15:53:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/qa/test_report_dashboard_inventory.py
summary: Stabilized the QA dashboard inventory help contract by moving the fragile
  assertion to in-process main(argv) execution and exposing an argv seam on report_dashboard_inventory.main
  while keeping router coverage explicit.
---

# Episodic summary

## Task

- Title: Fix dashboard inventory CLI help timeout

## Outcome

- Stabilized the QA dashboard inventory help contract by moving the fragile assertion to in-process main(argv) execution and exposing an argv seam on report_dashboard_inventory.main while keeping router coverage explicit.

## Lessons learned

- Replace with durable follow-up if needed
