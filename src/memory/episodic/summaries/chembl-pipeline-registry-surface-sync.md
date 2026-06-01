---
id: chembl-pipeline-registry-surface-sync
title: Sync ChEMBL pipeline export surface with registry
task_id: chembl-pipeline-registry-surface-sync
created_at: '2026-06-01T06:59:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/factories/pipeline/test_registry_consistency.py
summary: Added ChEMBLTargetProteinClassificationPipeline to the canonical ChEMBL pipeline
  marker/export surface and exported TargetProteinClassificationTransformer from bioetl.application.pipelines.chembl.
  Verified the targeted and full registry consistency unit tests pass. Attempted module-coverage
  inventory hash refresh per post-change policy, but source_tree_sha256 is currently
  unstable because repeated compute_source_tree_sha256 calls return different values
  on the active dirty checkout.
---

# Episodic summary

## Task

- Title: Sync ChEMBL pipeline export surface with registry

## Outcome

- Added ChEMBLTargetProteinClassificationPipeline to the canonical ChEMBL pipeline marker/export surface and exported TargetProteinClassificationTransformer from bioetl.application.pipelines.chembl. Verified the targeted and full registry consistency unit tests pass. Attempted module-coverage inventory hash refresh per post-change policy, but source_tree_sha256 is currently unstable because repeated compute_source_tree_sha256 calls return different values on the active dirty checkout.

## Lessons learned

- Replace with durable follow-up if needed
