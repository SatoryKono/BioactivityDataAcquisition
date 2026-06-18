---
id: fix-checkpoint-metadata-runmanifest-provenance
title: Fix checkpoint metadata helper strict RunManifest provenance failure
task_id: fix-checkpoint-metadata-runmanifest-provenance
created_at: '2026-06-18T17:54:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/factories/pipeline/test_checkpoint_metadata_helpers.py
- src/bioetl/application/services/control_plane/manifest/validation.py
summary: Active task session context.
query: test_checkpoint_metadata_execution_fingerprint_matches_manifest_contract strict
  RunManifest provenance contract_schema_hash dq_policy_ref rule_bundle_version checkpoint
  metadata
---

# Session note

## Task

- Title: Fix checkpoint metadata helper strict RunManifest provenance failure
- Retrieval query: test_checkpoint_metadata_execution_fingerprint_matches_manifest_contract strict RunManifest provenance contract_schema_hash dq_policy_ref rule_bundle_version checkpoint metadata

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
