---
id: grafana-selector-scope-investigation
title: Investigate workflow/pipeline run-id selector scope
task_id: grafana-selector-scope-investigation
created_at: '2026-06-01T18:23:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/control_plane_selector_context.py
summary: 'Investigated Grafana Workflow/Pipeline/Run Type/Run ID selector formation.
  Workflow comes from bioetl_workflow_runs_total.workflow; pipeline and run_type come
  from bioetl_records_processed_total labels; run_id comes from /ops/control-plane/filter-options
  over local run-manifest catalog. Root cause of cross-pipeline run_id values is fail-open
  fallback in control_plane_selector_context._narrow_manifest_catalog: when the selected
  workflow/pipeline/run_type scope matches zero manifests, it returns the full manifest
  catalog (return narrowed if narrowed else manifests), and build_selector_filter_options_payload
  then uses candidates if candidates else records, causing Run ID options to include
  unrelated pipelines such as chembl_assay.'
---

# Episodic summary

## Task

- Title: Investigate workflow/pipeline run-id selector scope

## Outcome

- Investigated Grafana Workflow/Pipeline/Run Type/Run ID selector formation. Workflow comes from bioetl_workflow_runs_total.workflow; pipeline and run_type come from bioetl_records_processed_total labels; run_id comes from /ops/control-plane/filter-options over local run-manifest catalog. Root cause of cross-pipeline run_id values is fail-open fallback in control_plane_selector_context._narrow_manifest_catalog: when the selected workflow/pipeline/run_type scope matches zero manifests, it returns the full manifest catalog (return narrowed if narrowed else manifests), and build_selector_filter_options_payload then uses candidates if candidates else records, causing Run ID options to include unrelated pipelines such as chembl_assay.

## Lessons learned

- Replace with durable follow-up if needed
