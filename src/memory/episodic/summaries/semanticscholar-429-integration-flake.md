---
id: semanticscholar-429-integration-flake
title: Debug Semantic Scholar integration 429 flake
task_id: semanticscholar-429-integration-flake
created_at: '2026-06-03T11:08:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/test_semanticscholar.py
summary: Fixed Semantic Scholar integration flake by replacing three live rate-limit-sensitive
  search/fallback tests with deterministic respx endpoint responses while keeping
  real adapter and HTTP client flows under test.
---

# Episodic summary

## Task

- Title: Debug Semantic Scholar integration 429 flake

## Outcome

- Fixed Semantic Scholar integration flake by replacing three live rate-limit-sensitive search/fallback tests with deterministic respx endpoint responses while keeping real adapter and HTTP client flows under test.

## Lessons learned

- Replace with durable follow-up if needed
