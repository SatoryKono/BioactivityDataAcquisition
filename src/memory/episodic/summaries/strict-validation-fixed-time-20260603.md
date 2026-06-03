---
id: strict-validation-fixed-time-20260603
title: Replace datetime.now in strict validation tests
task_id: strict-validation-fixed-time-20260603
created_at: '2026-06-03T07:38:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/storage/gold/test_strict_validation.py
summary: Replaced datetime.now with a fixed test timestamp in gold strict validation
  tests and synced the same file to current ScdConfig, pandera import, and validation
  error message contracts.
---

# Episodic summary

## Task

- Title: Replace datetime.now in strict validation tests

## Outcome

- Replaced datetime.now with a fixed test timestamp in gold strict validation tests and synced the same file to current ScdConfig, pandera import, and validation error message contracts.

## Lessons learned

- Replace with durable follow-up if needed
