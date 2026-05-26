---
id: fix-reproducibility-contract-inventory-import
title: Fix reproducibility contract inventory import
task_id: fix-reproducibility-contract-inventory-import
created_at: '2026-05-26T06:19:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_reproducibility_contract_suite.py
summary: Restored the _make_merge_metrics_mixin test helper in the reproducibility
  contract suite by adding a concrete MergeMetricsRecorderMixin harness. Validated
  Windows inventory module, selected suite test, ruff check, and py_compile.
---

# Episodic summary

## Task

- Title: Fix reproducibility contract inventory import

## Outcome

- Restored the _make_merge_metrics_mixin test helper in the reproducibility contract suite by adding a concrete MergeMetricsRecorderMixin harness. Validated Windows inventory module, selected suite test, ruff check, and py_compile.

## Lessons learned

- Replace with durable follow-up if needed
