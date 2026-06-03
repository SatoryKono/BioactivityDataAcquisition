---
id: debug-cli-main-registry-20260603
title: Debug CLI main registry prebuild
task_id: debug-cli-main-registry-20260603
created_at: '2026-06-03T06:05:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
summary: Restored lazy CLI main entrypoint behavior by removing eager registry construction
  from main(), and synchronized the stale main-entrypoint unit test to the thin-wrapper
  contract; targeted main tests now pass.
---

# Episodic summary

## Task

- Title: Debug CLI main registry prebuild

## Outcome

- Restored lazy CLI main entrypoint behavior by removing eager registry construction from main(), and synchronized the stale main-entrypoint unit test to the thin-wrapper contract; targeted main tests now pass.

## Lessons learned

- Replace with durable follow-up if needed
