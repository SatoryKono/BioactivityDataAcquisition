---
id: semantic-etl-full-audit-refresh-2026-05-15
title: Full semantic ETL pipeline audit refresh
task_id: semantic-etl-full-audit-refresh-2026-05-15
created_at: '2026-05-15T08:57:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json
summary: 'Regenerated and verified full BioETL semantic ETL audit artifacts. Current
  snapshot: 287 semantic clusters, 1154 fields, 26 pipelines, 3248 pair rows, all
  Drift Risk LOW, no CRITICAL/HIGH/MEDIUM rows, no Normalization=DIFFERENT/CONFLICTING
  rows, no Validation=DIFFERENT/STRICTNESS_MISMATCH rows, no Typing=CONFLICTING rows.
  Checks passed: report-semantic-pipeline-audit --check, check-semantic-pair-budget,
  check-semantic-registry-drift, check-semantic-anchor-parity, check-generic-field-ownership,
  validate-configs, schema artifact check, normalization matrix check, and targeted
  semantic pytest suite.'
---

# Episodic summary

## Task

- Title: Full semantic ETL pipeline audit refresh

## Outcome

- Regenerated and verified full BioETL semantic ETL audit artifacts. Current snapshot: 287 semantic clusters, 1154 fields, 26 pipelines, 3248 pair rows, all Drift Risk LOW, no CRITICAL/HIGH/MEDIUM rows, no Normalization=DIFFERENT/CONFLICTING rows, no Validation=DIFFERENT/STRICTNESS_MISMATCH rows, no Typing=CONFLICTING rows. Checks passed: report-semantic-pipeline-audit --check, check-semantic-pair-budget, check-semantic-registry-drift, check-semantic-anchor-parity, check-generic-field-ownership, validate-configs, schema artifact check, normalization matrix check, and targeted semantic pytest suite.

## Lessons learned

- Replace with durable follow-up if needed
