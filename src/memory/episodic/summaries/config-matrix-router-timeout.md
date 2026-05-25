---
id: config-matrix-router-timeout
title: Fix Windows timeout in scripts.schema generate-config-matrix router dispatch
task_id: config-matrix-router-timeout
created_at: '2026-05-25T16:55:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/common/cli_dispatch.py
summary: Updated shared CLI module dispatch to call target main() in-process, eliminating
  nested Python subprocesses that can hang under captured stdout/stderr on Windows.
  Added regression tests for argv and sys.argv-based module mains.
---

# Episodic summary

## Task

- Title: Fix Windows timeout in scripts.schema generate-config-matrix router dispatch

## Outcome

- Updated shared CLI module dispatch to call target main() in-process, eliminating nested Python subprocesses that can hang under captured stdout/stderr on Windows. Added regression tests for argv and sys.argv-based module mains.

## Lessons learned

- Replace with durable follow-up if needed
