---
id: record-normalization-core-nameerror-20260602
title: Fix ContentHashPolicyByVersion NameError in record normalization core tests
task_id: record-normalization-core-nameerror-20260602
created_at: '2026-06-02T16:26:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/core/normalization_test_support.py
summary: Restored normalization_test_support.py as an explicit test-only re-export
  facade for ContentHashPolicyByVersion, ContentHashVersionPolicy, PreSilverRecord,
  NormalizationContractError, cast, MagicMock, and Hypothesis helpers. This fixed
  NameError regressions in split record-normalization tests; targeted normalization
  suite passed 60/60 and ruff passed.
---

# Episodic summary

## Task

- Title: Fix ContentHashPolicyByVersion NameError in record normalization core tests

## Outcome

- Restored normalization_test_support.py as an explicit test-only re-export facade for ContentHashPolicyByVersion, ContentHashVersionPolicy, PreSilverRecord, NormalizationContractError, cast, MagicMock, and Hypothesis helpers. This fixed NameError regressions in split record-normalization tests; targeted normalization suite passed 60/60 and ruff passed.

## Lessons learned

- Replace with durable follow-up if needed
