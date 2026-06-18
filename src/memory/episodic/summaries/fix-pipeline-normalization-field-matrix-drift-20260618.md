---
id: fix-pipeline-normalization-field-matrix-drift-20260618
title: Fix pipeline normalization field matrix artifact drift
task_id: fix-pipeline-normalization-field-matrix-drift-20260618
created_at: '2026-06-18T06:33:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.csv
- docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md
- docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md
- tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py
summary: Regenerated pipeline_normalization_field_matrix generated CSV/Markdown artifacts
  to match current generator output after composite_target gained explicit target-protein-classification
  fields. Confirmed check_artifacts, full generator unit tests, normalization governance
  CLI smoke, surface ratchet tests, diff check, and docs link checks pass.
---

# Episodic summary

## Task

- Title: Fix pipeline normalization field matrix artifact drift

## Outcome

- Regenerated pipeline_normalization_field_matrix generated CSV/Markdown artifacts to match current generator output after composite_target gained explicit target-protein-classification fields. Confirmed check_artifacts, full generator unit tests, normalization governance CLI smoke, surface ratchet tests, diff check, and docs link checks pass.

## Lessons learned

- Replace with durable follow-up if needed
