---
id: contract-test-skip-reasons
title: inspect-contract-test-skips
task_id: contract-test-skip-reasons
created_at: '2026-05-24T17:51:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/conftest.py
summary: 'Inspected tests/contract skip behavior. Current local run collects 1001
  tests with 98 skips, all caused by explicit contract-suite gates: live API disabled
  for provider contract tests and network disabled for network-marked no_api contract
  checks. Silver schema contract subset currently has no skips despite stale skipped-tests
  analysis documentation.'
---

# Episodic summary

## Task

- Title: inspect-contract-test-skips

## Outcome

- Inspected tests/contract skip behavior. Current local run collects 1001 tests with 98 skips, all caused by explicit contract-suite gates: live API disabled for provider contract tests and network disabled for network-marked no_api contract checks. Silver schema contract subset currently has no skips despite stale skipped-tests analysis documentation.

## Lessons learned

- Replace with durable follow-up if needed
