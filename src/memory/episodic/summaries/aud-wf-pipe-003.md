---
id: aud-wf-pipe-003
title: Audit all workflows and pipelines with dashboard surface verification and fix
  confirmed defects
task_id: AUD-WF-PIPE-003
created_at: '2026-05-20T07:35:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Completed stage-0 inventory for 25 workflows and 26 pipelines (21 workflow-managed
  entity pipelines plus 5 standalone composites). Executed bounded live workflow chembl_activity
  successfully with workflow_run_id=259569e0-cad5-4e0c-850e-4823fef558d2 and verified
  Prometheus/Loki/dashboard backend evidence. Confirmed and partially fixed dashboard
  backend defects: added selector prefilter regression coverage and removed replay-helper
  import cycle from run-manifest diagnostics cold-start path. Re-audit shows health/identity/stats
  endpoints working, but control-plane run_id filter-options and quarantine filtered-records
  endpoints still time out on cold restart scope; full remaining workflow/pipeline
  matrix is not verifiable in current audit window due live-run cost and composite
  prerequisites.'
---

# Episodic summary

## Task

- Title: Audit all workflows and pipelines with dashboard surface verification and fix confirmed defects

## Outcome

- Completed stage-0 inventory for 25 workflows and 26 pipelines (21 workflow-managed entity pipelines plus 5 standalone composites). Executed bounded live workflow chembl_activity successfully with workflow_run_id=259569e0-cad5-4e0c-850e-4823fef558d2 and verified Prometheus/Loki/dashboard backend evidence. Confirmed and partially fixed dashboard backend defects: added selector prefilter regression coverage and removed replay-helper import cycle from run-manifest diagnostics cold-start path. Re-audit shows health/identity/stats endpoints working, but control-plane run_id filter-options and quarantine filtered-records endpoints still time out on cold restart scope; full remaining workflow/pipeline matrix is not verifiable in current audit window due live-run cost and composite prerequisites.

## Lessons learned

- Replace with durable follow-up if needed
