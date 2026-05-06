---
id: grafana-control-plane-missing-telemetry
title: Fix Control Plane missing telemetry PromQL
task_id: grafana-control-plane-missing-telemetry
created_at: '2026-05-06T12:36:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: Updated bioetl-control-plane-v1 trust panels so missing control-plane/replay
  telemetry is not masked with or vector(0). Replay Safety State and Replay / Resume
  Blockers now preserve No data/UNKNOWN for missing metric families, and Replay Lag
  Seconds no longer converts missing lag telemetry to 0. Verified JSON validity and
  full Grafana config integration suite.
---

# Episodic summary

## Task

- Title: Fix Control Plane missing telemetry PromQL

## Outcome

- Updated bioetl-control-plane-v1 trust panels so missing control-plane/replay telemetry is not masked with or vector(0). Replay Safety State and Replay / Resume Blockers now preserve No data/UNKNOWN for missing metric families, and Replay Lag Seconds no longer converts missing lag telemetry to 0. Verified JSON validity and full Grafana config integration suite.

## Lessons learned

- Replace with durable follow-up if needed
