---
id: chembl-audit-issue-triage
title: Triage and create ChEMBL target xref governance issue
task_id: chembl-audit-issue-triage
created_at: '2026-05-05T17:44:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/vocab/chembl_reference_sources.yaml
summary: 'Checked the ChEMBL target xref source database audit draft against current
  repo state. Found that configs/vocab/chembl_reference_sources.yaml already exists
  and fixture subset tests already check observed nested xref_src_db values, so the
  original draft was partly stale. Created GitHub issue #3751 with narrowed scope
  to complete nested source_fields/profile governance for chembl_target.target_components[].target_component_xrefs[].xref_src_db
  and chembl_target_component.target_component_xrefs[].xref_src_db.'
---

# Episodic summary

## Task

- Title: Triage and create ChEMBL target xref governance issue

## Outcome

- Checked the ChEMBL target xref source database audit draft against current repo state. Found that configs/vocab/chembl_reference_sources.yaml already exists and fixture subset tests already check observed nested xref_src_db values, so the original draft was partly stale. Created GitHub issue #3751 with narrowed scope to complete nested source_fields/profile governance for chembl_target.target_components[].target_component_xrefs[].xref_src_db and chembl_target_component.target_component_xrefs[].xref_src_db.

## Lessons learned

- Replace with durable follow-up if needed
