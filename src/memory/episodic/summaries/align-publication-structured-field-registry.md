---
id: align-publication-structured-field-registry
title: Align publication structured-field registry with profile surfaces
task_id: align-publication-structured-field-registry
created_at: '2026-05-19T12:07:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/normalization/_publication_structured_field_policy_specs.py
- tests/unit/domain/normalization/test_publication_structured_fields.py
- docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.csv
- docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md
summary: Added the missing Crossref structured sidecar policies for author_details
  and references raw/canonical JSON fields to the publication structured-field policy
  spec, regenerated the pipeline normalization field matrix artifacts, and verified
  the structured-field unit tests plus matrix committed-artifact checks pass.
---

# Episodic summary

## Task

- Title: Align publication structured-field registry with profile surfaces

## Outcome

- Added the missing Crossref structured sidecar policies for author_details and references raw/canonical JSON fields to the publication structured-field policy spec, regenerated the pipeline normalization field matrix artifacts, and verified the structured-field unit tests plus matrix committed-artifact checks pass.

## Lessons learned

- Replace with durable follow-up if needed
