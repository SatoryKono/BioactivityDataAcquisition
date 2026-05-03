---
id: implement-3574-control-plane-replay-safety-dashboard
title: Implement issue 3574 Control Plane Replay Safety dashboard
task_id: implement-3574-control-plane-replay-safety-dashboard
created_at: '2026-05-03T06:43:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3574
summary: Redesigned bioetl-control-plane-v1 into Control Plane / Replay Safety with
  a seven-panel replay/resume answer row, manifest/ledger ratios, checkpoint/replay
  diagnostics, GLOBAL read diagnostics, audit/lineage diagnostics, and missing-signal
  blind spots for checkpoint age and replay duplicate metrics. Updated Grafana integration
  tests and operator docs; fixed runtime Loki drilldown titles/queries to satisfy
  dashboard-link contract.
---

# Episodic summary

## Task

- Title: Implement issue 3574 Control Plane Replay Safety dashboard

## Outcome

- Redesigned bioetl-control-plane-v1 into Control Plane / Replay Safety with a seven-panel replay/resume answer row, manifest/ledger ratios, checkpoint/replay diagnostics, GLOBAL read diagnostics, audit/lineage diagnostics, and missing-signal blind spots for checkpoint age and replay duplicate metrics. Updated Grafana integration tests and operator docs; fixed runtime Loki drilldown titles/queries to satisfy dashboard-link contract.

## Lessons learned

- Replace with durable follow-up if needed
