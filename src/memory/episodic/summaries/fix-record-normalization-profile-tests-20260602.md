---
id: fix-record-normalization-profile-tests-20260602
title: Fix record normalization profile test NameErrors
task_id: fix-record-normalization-profile-tests-20260602
created_at: '2026-06-02T16:24:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed explicit test imports in test_record_normalization_profiles.py after
  wildcard support no longer re-exported NormalizationContractError, MagicMock, PreSilverRecord,
  or cast. Verified ruff and the full target test module pass.
---

# Episodic summary

## Task

- Title: Fix record normalization profile test NameErrors

## Outcome

- Fixed explicit test imports in test_record_normalization_profiles.py after wildcard support no longer re-exported NormalizationContractError, MagicMock, PreSilverRecord, or cast. Verified ruff and the full target test module pass.

## Lessons learned

- Replace with durable follow-up if needed
