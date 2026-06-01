---
id: chembl-target-protein-class-enrichment-20260601
title: Fill chembl_target protein classification fields
task_id: chembl-target-protein-class-enrichment-20260601
created_at: '2026-06-01T14:51:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/chembl/target_transformer.py
summary: 'Implemented and validated chembl_target protein classification enrichment
  path. Root causes: raw /target lacks protein_classifications; target transformer
  previously only saw nested payload; ChEMBL root protein_class parent_id=0 must be
  treated as absent parent to avoid quarantined classification rows. Validated live
  chembl_target runs: limit=5 populated protein_classifications and L1-L4 where source
  hierarchy depth exists; filtered CHEMBL6115 populated L1-L5 in Silver and Gold.
  Ran targeted unit, schema/contract, ruff, module coverage inventory refresh, hash
  guard, and composition architecture check.'
---

# Episodic summary

## Task

- Title: Fill chembl_target protein classification fields

## Outcome

- Implemented and validated chembl_target protein classification enrichment path. Root causes: raw /target lacks protein_classifications; target transformer previously only saw nested payload; ChEMBL root protein_class parent_id=0 must be treated as absent parent to avoid quarantined classification rows. Validated live chembl_target runs: limit=5 populated protein_classifications and L1-L4 where source hierarchy depth exists; filtered CHEMBL6115 populated L1-L5 in Silver and Gold. Ran targeted unit, schema/contract, ruff, module coverage inventory refresh, hash guard, and composition architecture check.

## Lessons learned

- Replace with durable follow-up if needed
