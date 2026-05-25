---
id: fix-runtime-cardinality-evidence-20260525
title: Restore runtime cardinality evidence artifact
task_id: fix-runtime-cardinality-evidence-20260525
created_at: '2026-05-25T12:59:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_observability_metric_governance.py
- reports/observability/runtime_cardinality_inventory.json
summary: Restored the governed runtime cardinality evidence artifact, unignored its
  canonical reports/observability path, aligned the architecture assertion with the
  inventory script reviewed/required contract, and verified observability metric governance
  tests.
---

# Episodic summary

## Task

- Title: Restore runtime cardinality evidence artifact

## Outcome

- Restored the governed runtime cardinality evidence artifact, unignored its canonical reports/observability path, aligned the architecture assertion with the inventory script reviewed/required contract, and verified observability metric governance tests.

## Lessons learned

- Governed reports under ignored parent directories need explicit `.gitignore`
  negation rules; otherwise clean checkouts miss required evidence artifacts
  even when local generated files exist.
