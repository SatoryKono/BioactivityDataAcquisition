---
id: grafana-trust-panel-semantics
title: Reconcile Grafana control-plane trust panel no-data semantics
task_id: grafana-trust-panel-semantics
created_at: '2026-05-06T13:59:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: Removed zero fallbacks from Replay Safety State, Replay / Resume Blockers,
  and Replay Lag Seconds trust surfaces in bioetl-control-plane-v1.json; updated integration
  expectations so only true count-like summary panels require or vector(0).
---

# Episodic summary

## Task

- Title: Reconcile Grafana control-plane trust panel no-data semantics

## Outcome

- Removed zero fallbacks from Replay Safety State, Replay / Resume Blockers, and Replay Lag Seconds trust surfaces in bioetl-control-plane-v1.json; updated integration expectations so only true count-like summary panels require or vector(0).

## Lessons learned

- Replace with durable follow-up if needed
