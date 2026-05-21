---
id: investigate-id-panel-connection-refused
title: Fix ID panel Grafana backend bind mismatch
task_id: investigate-id-panel-connection-refused
created_at: '2026-05-21T09:12:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
summary: Changed quarantine serve default host from 127.0.0.1 to 0.0.0.0 so Grafana
  container can reach the Quarantine Explorer backend via host.docker.internal:8081;
  updated grafana README launcher guidance and synced provisioning tests; intentionally
  left .env.example unchanged due env-file edit guardrail.
---

# Episodic summary

## Task

- Title: Fix ID panel Grafana backend bind mismatch

## Outcome

- Changed quarantine serve default host from 127.0.0.1 to 0.0.0.0 so Grafana container can reach the Quarantine Explorer backend via host.docker.internal:8081; updated grafana README launcher guidance and synced provisioning tests; intentionally left .env.example unchanged due env-file edit guardrail.

## Lessons learned

- Replace with durable follow-up if needed
