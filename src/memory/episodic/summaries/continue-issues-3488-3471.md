---
id: continue-issues-3488-3471
title: Complete issues 3488 and 3471
task_id: continue-issues-3488-3471
created_at: '2026-05-02T08:28:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- github-issues-3488-3471
summary: Corrected unsafe monitoring PromQL examples by aggregating histogram buckets
  with sum by (le, ...) and converting raw error threshold examples to denominator-based
  rates. Defined semantic_execution_equivalence and artifact_byte_equivalence in run
  manifest contract docs and inspection runbook, including occurrence-only fields
  and sidecar content_hash semantics. Added architecture docs guards for unsafe PromQL
  examples and replay equivalence terminology. Validated with targeted architecture
  tests, broader observability docs subset, reproducibility docs subset, ruff, and
  git diff --check.
---

# Episodic summary

## Task

- Title: Complete issues 3488 and 3471

## Outcome

- Corrected unsafe monitoring PromQL examples by aggregating histogram buckets with sum by (le, ...) and converting raw error threshold examples to denominator-based rates. Defined semantic_execution_equivalence and artifact_byte_equivalence in run manifest contract docs and inspection runbook, including occurrence-only fields and sidecar content_hash semantics. Added architecture docs guards for unsafe PromQL examples and replay equivalence terminology. Validated with targeted architecture tests, broader observability docs subset, reproducibility docs subset, ruff, and git diff --check.

## Lessons learned

- Replace with durable follow-up if needed
