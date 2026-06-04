---
id: issue-5052-close
title: 'Close #5052 lineage and debug-export service hotspot ratchet'
task_id: issue-5052-close
created_at: '2026-06-04T07:45:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/lineage/metadata_lineage_node_builders.py
- src/bioetl/application/services/debug_export_service.py
- src/bioetl/application/services/export_manifests.py
- reports/quality/module-coverage-inventory.json
summary: Split lineage node builders, metadata coordinator, lineage inspection, metadata
  assembler facade, debug export collector/service, and export manifests below 250
  LOC; preserved public facades and debug/lineage/export behavior through targeted
  service tests; updated module coverage source tree hash.
---

# Episodic summary

## Task

- Title: Close #5052 lineage and debug-export service hotspot ratchet

## Outcome

- Split lineage node builders, metadata coordinator, lineage inspection, metadata assembler facade, debug export collector/service, and export manifests below 250 LOC; preserved public facades and debug/lineage/export behavior through targeted service tests; updated module coverage source tree hash.

## Lessons learned

- Replace with durable follow-up if needed
