---
id: issue-3749-append-idempotency-contract
title: Implement append-mode idempotency contract governance
task_id: issue-3749-append-idempotency-contract
created_at: '2026-05-06T07:22:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3749
summary: 'Implemented remaining #3749 safeguards: changed TableConfig and YAML-to-domain
  converter Gold default from append to SCD2, and strengthened tests/architecture/test_pipeline_config_idempotency_contract.py
  to scan base/entities/composites configs, support top-level sink and pipeline.sink
  formats, and require append-safe idempotency_contract values for append-mode Silver/Gold
  sinks. Targeted pytest passed for idempotency guard, TableConfig, write mode types,
  and run manifest support.'
---

# Episodic summary

## Task

- Title: Implement append-mode idempotency contract governance

## Outcome

- Implemented remaining #3749 safeguards: changed TableConfig and YAML-to-domain converter Gold default from append to SCD2, and strengthened tests/architecture/test_pipeline_config_idempotency_contract.py to scan base/entities/composites configs, support top-level sink and pipeline.sink formats, and require append-safe idempotency_contract values for append-mode Silver/Gold sinks. Targeted pytest passed for idempotency guard, TableConfig, write mode types, and run manifest support.

## Lessons learned

- Replace with durable follow-up if needed
