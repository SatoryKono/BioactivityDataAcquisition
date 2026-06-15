---
id: gh-5121-reject-observability-cli-split
title: Close GH-5121 split reject observability and CLI compatibility surfaces
task_id: gh-5121-reject-observability-cli-split
created_at: '2026-06-15T14:15:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5121
summary: 'Implemented GH-5121 split between Silver structural reject compatibility
  surfaces and Gold contract/semantic reject observability. Added DQ Gold reject outcomes
  panel using bioetl_processed_records_gold_quarantined_current and bioetl_processed_records_gold_excluded_by_contract_current,
  clarified Silver Reject Explorer as FILTERED_OUT_SILVER legacy alias only, updated
  quarantine/diagnostics CLI help and run result copy, synced dashboard/operator docs
  and generated inventories, refreshed module coverage inventory and architecture
  scorecard. Validation passed: ruff, targeted Prometheus/Grafana/CLI/architecture/docs
  checks, CLI command directory, docs links, silver boundary inventory, observability
  metric governance, module coverage direct hash compare.'
---

# Episodic summary

## Task

- Title: Close GH-5121 split reject observability and CLI compatibility surfaces

## Outcome

- Implemented GH-5121 split between Silver structural reject compatibility surfaces and Gold contract/semantic reject observability. Added DQ Gold reject outcomes panel using bioetl_processed_records_gold_quarantined_current and bioetl_processed_records_gold_excluded_by_contract_current, clarified Silver Reject Explorer as FILTERED_OUT_SILVER legacy alias only, updated quarantine/diagnostics CLI help and run result copy, synced dashboard/operator docs and generated inventories, refreshed module coverage inventory and architecture scorecard. Validation passed: ruff, targeted Prometheus/Grafana/CLI/architecture/docs checks, CLI command directory, docs links, silver boundary inventory, observability metric governance, module coverage direct hash compare.

## Lessons learned

- Replace with durable follow-up if needed
