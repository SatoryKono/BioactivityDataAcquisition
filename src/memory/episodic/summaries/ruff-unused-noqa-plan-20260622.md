---
id: ruff-unused-noqa-plan-20260622
title: Fix unused noqa in maintenance plan CLI
task_id: ruff-unused-noqa-plan-20260622
created_at: '2026-06-22T08:23:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/domains/maintenance/plan.py
summary: Removed stale noqa suppression from maintenance plan CLI import, sorted imports
  to satisfy ruff, refreshed module coverage inventory via scripts.engineering.qa
  report-module-coverage after src change, and verified test_regression_metrics.py::test_ruff_error_count
  passes. Module coverage hash guard is skipped by test policy on WSL.
---

# Episodic summary

## Task

- Title: Fix unused noqa in maintenance plan CLI

## Outcome

- Removed stale noqa suppression from maintenance plan CLI import, sorted imports to satisfy ruff, refreshed module coverage inventory via scripts.engineering.qa report-module-coverage after src change, and verified test_regression_metrics.py::test_ruff_error_count passes. Module coverage hash guard is skipped by test policy on WSL.

## Lessons learned

- Replace with durable follow-up if needed
