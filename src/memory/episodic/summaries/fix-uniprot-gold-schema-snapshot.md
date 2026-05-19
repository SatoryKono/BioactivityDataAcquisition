---
id: fix-uniprot-gold-schema-snapshot
title: Fix uniprot_protein gold schema snapshot drift
task_id: fix-uniprot-gold-schema-snapshot
created_at: '2026-05-19T06:28:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/fixtures/golden/gold/schema_registry.v1.json
summary: Updated gold schema snapshot registry for uniprot_protein to include canonical/raw
  structured payload fields already present in runtime schema and published contract;
  verified test_gold_schema_snapshot_registry passes.
---

# Episodic summary

## Task

- Title: Fix uniprot_protein gold schema snapshot drift

## Outcome

- Updated gold schema snapshot registry for uniprot_protein to include canonical/raw structured payload fields already present in runtime schema and published contract; verified test_gold_schema_snapshot_registry passes.

## Lessons learned

- Replace with durable follow-up if needed
