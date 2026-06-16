---
id: fix-test-governance-artifact-drift
title: Fix test governance artifact drift
task_id: fix-test-governance-artifact-drift
created_at: '2026-06-16T08:20:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/test-governance-current.json
summary: Refreshed test-governance-current.json to match the live collector after
  the test surface changed from 1755 to 1758 files and from 20580 to 20590 test functions.
  Duplicate-name inventory content stayed unchanged after LF normalization. Verified
  collector drift checks on Linux and Windows .venv-win, the specific artifact-drift
  architecture test, and the full test_test_governance_audit.py file.
---

# Episodic summary

## Task

- Title: Fix test governance artifact drift

## Outcome

- Refreshed test-governance-current.json to match the live collector after the test surface changed from 1755 to 1758 files and from 20580 to 20590 test functions. Duplicate-name inventory content stayed unchanged after LF normalization. Verified collector drift checks on Linux and Windows .venv-win, the specific artifact-drift architecture test, and the full test_test_governance_audit.py file.

## Lessons learned

- Replace with durable follow-up if needed
