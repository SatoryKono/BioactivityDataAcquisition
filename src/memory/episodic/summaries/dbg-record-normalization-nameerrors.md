---
id: dbg-record-normalization-nameerrors
title: Fix NameError regressions in record normalization unit tests
task_id: dbg-record-normalization-nameerrors
created_at: '2026-06-02T08:16:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/core/normalization_test_support.py
summary: Restored missing test-support imports/exports in normalization_test_support.py
  so split normalization unit modules regain ContentHashPolicyByVersion, PreSilverRecord,
  NormalizationContractError, MagicMock, cast, and Hypothesis helpers.
---

# Episodic summary

## Task

- Title: Fix NameError regressions in record normalization unit tests

## Outcome

- Restored missing test-support imports/exports in normalization_test_support.py so split normalization unit modules regain ContentHashPolicyByVersion, PreSilverRecord, NormalizationContractError, MagicMock, cast, and Hypothesis helpers.

## Lessons learned

- Replace with durable follow-up if needed
