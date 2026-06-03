---
id: asyncio-idle-timeout-no-nodeid
title: Debug pytest asyncio idle timeout without nodeid
task_id: asyncio-idle-timeout-no-nodeid
created_at: '2026-06-03T10:21:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/conftest.py
summary: 'Added Windows/PyCharm-oriented async pytest timeout diagnostics in tests/conftest.py:
  a watchdog starts for async tests and dumps nodeid plus pending asyncio task stacks
  shortly before pytest-timeout aborts. Verified synthetic dump, ruff, async smoke,
  CLI smoke, test-governance guards, and ruff regression metric.'
---

# Episodic summary

## Task

- Title: Debug pytest asyncio idle timeout without nodeid

## Outcome

- Added Windows/PyCharm-oriented async pytest timeout diagnostics in tests/conftest.py: a watchdog starts for async tests and dumps nodeid plus pending asyncio task stacks shortly before pytest-timeout aborts. Verified synthetic dump, ruff, async smoke, CLI smoke, test-governance guards, and ruff regression metric.

## Lessons learned

- Replace with durable follow-up if needed
