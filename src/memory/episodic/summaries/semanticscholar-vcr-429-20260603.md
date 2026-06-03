---
id: semanticscholar-vcr-429-20260603
title: Fix Semantic Scholar integration tests hitting live 429
task_id: semanticscholar-vcr-429-20260603
created_at: '2026-06-03T11:06:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/conftest.py
summary: Added repo-local vcrpy fallback for @pytest.mark.vcr when pytest-recording
  is absent, added default cassette fixtures in tests/conftest.py, and mapped Semantic
  Scholar integration tests to committed cassette names.
---

# Episodic summary

## Task

- Title: Fix Semantic Scholar integration tests hitting live 429

## Outcome

- Added repo-local vcrpy fallback for @pytest.mark.vcr when pytest-recording is absent, added default cassette fixtures in tests/conftest.py, and mapped Semantic Scholar integration tests to committed cassette names.

## Lessons learned

- Replace with durable follow-up if needed
