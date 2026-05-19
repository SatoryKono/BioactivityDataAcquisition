---
id: fix-chembl-assay-required-field-reporting
title: Fix ChEMBL assay required-field reporting
task_id: fix-chembl-assay-required-field-reporting
created_at: '2026-05-18T18:58:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/pipelines/chembl/test_assay_transformer_required_fields.py
summary: Investigated stale chembl_assay required-field failures. Current config requires
  description, not assay_description; current checkout reproduces passing required-fields
  tests and assay pipeline transform test. No code changes needed.
---

# Episodic summary

## Task

- Title: Fix ChEMBL assay required-field reporting

## Outcome

- Investigated stale chembl_assay required-field failures. Current config requires description, not assay_description; current checkout reproduces passing required-fields tests and assay pipeline transform test. No code changes needed.

## Lessons learned

- Replace with durable follow-up if needed
