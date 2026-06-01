---
id: pipeline-matrix-target-protein-classification-20260601
title: Fix target protein classification pipeline matrix drift
task_id: pipeline-matrix-target-protein-classification-20260601
created_at: '2026-06-01T07:26:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_pipeline_matrix_e2e.py
summary: Synchronized chembl_target_protein_classification across observed-vocab count,
  e2e pipeline matrix, CLI list-pipelines snapshot, single-pipeline workflow wrapper,
  and workflow docs/mirror. Deferred the new E2E matrix case because no cassette is
  present. Verified observed-vocab, pipeline matrix, e2e deferred-policy, workflow
  wrapper, and CLI registry tests.
---

# Episodic summary

## Task

- Title: Fix target protein classification pipeline matrix drift

## Outcome

- Synchronized chembl_target_protein_classification across observed-vocab count, e2e pipeline matrix, CLI list-pipelines snapshot, single-pipeline workflow wrapper, and workflow docs/mirror. Deferred the new E2E matrix case because no cassette is present. Verified observed-vocab, pipeline matrix, e2e deferred-policy, workflow wrapper, and CLI registry tests.

## Lessons learned

- Replace with durable follow-up if needed
