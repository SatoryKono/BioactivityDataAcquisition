---
id: winerror-10055-debug
title: Debug pytest WinError 10055
task_id: winerror-10055-debug
created_at: '2026-06-17T06:05:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/dev/run_tests.py
summary: Capped Windows xdist worker defaults in developer pytest runners to reduce
  socket-buffer exhaustion and verified the guard with focused tests.
---

# Episodic summary

## Task

- Title: Debug pytest WinError 10055

## Outcome

- Capped Windows xdist worker defaults in developer pytest runners to reduce socket-buffer exhaustion and verified the guard with focused tests.

## Lessons learned

- Replace with durable follow-up if needed
