---
id: global-vcr-name-resolution-20260603
title: Fix global VCR cassette name resolution for class-based tests
task_id: global-vcr-name-resolution-20260603
created_at: '2026-06-03T11:17:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/conftest.py
summary: Updated the global VCR cassette fallback to prefer committed ClassName.test_name
  stems before bare test names, so class-based integration and pipeline tests stop
  skipping on missing bare cassette files.
---

# Episodic summary

## Task

- Title: Fix global VCR cassette name resolution for class-based tests

## Outcome

- Updated the global VCR cassette fallback to prefer committed ClassName.test_name stems before bare test names, so class-based integration and pipeline tests stop skipping on missing bare cassette files.

## Lessons learned

- Replace with durable follow-up if needed
