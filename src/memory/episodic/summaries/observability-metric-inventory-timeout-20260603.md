---
id: observability-metric-inventory-timeout-20260603
title: Fix observability metric inventory timeout
task_id: observability-metric-inventory-timeout-20260603
created_at: '2026-06-03T17:58:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_observability_metric_inventory.py
summary: Fixed observability metric inventory timeout by preventing direct doc corpus
  reads in real git checkouts when bounded scanners are unavailable, adding rg fallback
  after git grep, and replacing temp-file discovery capture with bounded subprocess
  capture. Verified unit inventory tests and runtime metric emission consistency in
  WSL and Windows .venv-win.
---

# Episodic summary

## Task

- Title: Fix observability metric inventory timeout

## Outcome

- Fixed observability metric inventory timeout by preventing direct doc corpus reads in real git checkouts when bounded scanners are unavailable, adding rg fallback after git grep, and replacing temp-file discovery capture with bounded subprocess capture. Verified unit inventory tests and runtime metric emission consistency in WSL and Windows .venv-win.

## Lessons learned

- Replace with durable follow-up if needed
