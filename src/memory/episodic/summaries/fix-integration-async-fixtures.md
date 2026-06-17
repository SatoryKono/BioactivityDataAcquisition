---
id: fix-integration-async-fixtures
title: Fix integration pytest async handling and shared fixtures
task_id: fix-integration-async-fixtures
created_at: '2026-06-17T09:34:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Enabled shared metadata and ChEMBL extraction pytest fixtures, added a non-auto
  asyncio fallback for unmarked coroutine tests, and converted the checkpoint async
  fixture to pytest_asyncio.fixture. Targeted integration, strict-mode async, ruff
  check, and ruff format checks passed.
---

# Episodic summary

## Task

- Title: Fix integration pytest async handling and shared fixtures

## Outcome

- Enabled shared metadata and ChEMBL extraction pytest fixtures, added a non-auto asyncio fallback for unmarked coroutine tests, and converted the checkpoint async fixture to pytest_asyncio.fixture. Targeted integration, strict-mode async, ruff check, and ruff format checks passed.

## Lessons learned

- Replace with durable follow-up if needed
