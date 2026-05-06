---
id: audit-011-lineage-builder-naming
title: Rename lineage metadata assembler factory dependencies to builders
task_id: audit-011-lineage-builder-naming
created_at: '2026-05-06T08:48:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/lineage/metadata_assembler_support.py
- src/bioetl/application/services/lineage/metadata_assemblers.py
- src/bioetl/application/services/lineage/metadata_coordinator.py
- tests/unit/application/services/test_metadata_assemblers.py
summary: Renamed lineage metadata assembler callable dependency protocols and dataclass
  fields from factory terminology to builder terminology; updated coordinator wiring
  and unit regression coverage.
---

# Episodic summary

## Task

- Title: Rename lineage metadata assembler factory dependencies to builders

## Outcome

- Renamed lineage metadata assembler callable dependency protocols and dataclass fields from factory terminology to builder terminology; updated coordinator wiring and unit regression coverage.

## Lessons learned

- Replace with durable follow-up if needed
