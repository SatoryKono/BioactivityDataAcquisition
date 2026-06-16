---
id: pytest-asyncio-hook-windows-fix
title: Fix Windows pytest asyncio hook validation
task_id: pytest-asyncio-hook-windows-fix
created_at: '2026-06-16T12:22:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/conftest.py
summary: Guarded Windows-only pytest_asyncio_loop_factories hook registration so stale
  pytest-asyncio 1.3.0 envs stop failing collection while 1.4+ keeps selector-loop
  support.
---

# Episodic summary

## Task

- Title: Fix Windows pytest asyncio hook validation

## Outcome

- Guarded Windows-only pytest_asyncio_loop_factories hook registration so stale pytest-asyncio 1.3.0 envs stop failing collection while 1.4+ keeps selector-loop support.

## Lessons learned

- Replace with durable follow-up if needed
