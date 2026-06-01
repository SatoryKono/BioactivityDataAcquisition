---
id: duplicate-test-names-zero-plan-20260601
title: Plan duplicate_test_names reduction to zero
task_id: duplicate-test-names-zero-plan-20260601
created_at: '2026-06-01T12:59:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Prepared fact-based plan to reduce duplicate_test_names from 787 to 0. Baseline
  gathered from scripts.engineering.qa.report_test_governance_audit: 1633 test files,
  19373 test functions, 787 duplicate names, 2552 duplicate-name occurrences. Key
  hotspots are tests/unit/domain/value_objects/test_identifiers.py, publication schema
  validation suites, and generic names such as test_immutability/test_default_values/test_hash_consistency.
  Plan phases: visibility inventory, naming isolation, removal batches, and zero enforcement.'
---

# Episodic summary

## Task

- Title: Plan duplicate_test_names reduction to zero

## Outcome

- Prepared fact-based plan to reduce duplicate_test_names from 787 to 0. Baseline gathered from scripts.engineering.qa.report_test_governance_audit: 1633 test files, 19373 test functions, 787 duplicate names, 2552 duplicate-name occurrences. Key hotspots are tests/unit/domain/value_objects/test_identifiers.py, publication schema validation suites, and generic names such as test_immutability/test_default_values/test_hash_consistency. Plan phases: visibility inventory, naming isolation, removal batches, and zero enforcement.

## Lessons learned

- Replace with durable follow-up if needed
