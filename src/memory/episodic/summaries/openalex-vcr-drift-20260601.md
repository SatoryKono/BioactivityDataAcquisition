---
id: openalex-vcr-drift-20260601
title: Fix OpenAlex adapter VCR integration drift
task_id: openalex-vcr-drift-20260601
created_at: '2026-06-01T15:04:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/openalex/test_adapter.py
summary: Aligned OpenAlex adapter integration tests with committed legacy cassettes
  by adding class-qualified VCR cassette resolution and explicit overrides for renamed
  hashed tests; verified the full OpenAlex adapter integration module replays successfully
  in VCR record_mode=none.
---

# Episodic summary

## Task

- Title: Fix OpenAlex adapter VCR integration drift

## Outcome

- Aligned OpenAlex adapter integration tests with committed legacy cassettes by adding class-qualified VCR cassette resolution and explicit overrides for renamed hashed tests; verified the full OpenAlex adapter integration module replays successfully in VCR record_mode=none.

## Lessons learned

- Replace with durable follow-up if needed
