---
record_id: dashboard-no-data-capture-20260810
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 6901023af7b9dd7412f5325b8b8cf2937e1034fa
branch: fix/run-explorer-vars-again
worktree_id: b5393af69d37a674
task_id: dashboard-no-data-capture-20260810
actor:
  runtime: codex
  agent: observability-dashboard
  model: gpt-5.6-sol
created_at: '2026-08-10T15:30:47.960691+00:00'
source_refs:
- Capture.PNG
- grafana/dashboards/bioetl-run-explorer-v1.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 1a49a7243e31e2f93189166e47b3414a0f5ba56c4dab6a8eaaf1c518b3a79124
id: dashboard-no-data-capture-20260810
title: Diagnose Grafana dashboard no data
ttl_days: 14
confidence: episodic
summary: 'Diagnosed Capture.PNG Run Explorer valid-empty state: Prometheus and Ops
  HTTP are healthy; Run Explorer mixes Prometheus selectors with BioETL Ops HTTP.
  chembl_activity has control-plane manifest/ledger data but no reports/run-reports
  pipeline artifact, while chembl_assay has 80 report artifacts. Current container
  recreated after capture and sees the host report bind. Canonical bind verifier has
  a WSL lexical false positive comparing E:/ with /mnt/e.'
---

# Episodic summary

## Task

- Title: Diagnose Grafana dashboard no data

## Outcome

- Diagnosed Capture.PNG Run Explorer valid-empty state: Prometheus and Ops HTTP are healthy; Run Explorer mixes Prometheus selectors with BioETL Ops HTTP. chembl_activity has control-plane manifest/ledger data but no reports/run-reports pipeline artifact, while chembl_assay has 80 report artifacts. Current container recreated after capture and sees the host report bind. Canonical bind verifier has a WSL lexical false positive comparing E:/ with /mnt/e.

## Lessons learned

- Replace with durable follow-up if needed
