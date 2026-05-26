---
id: grafana-checkpoint-freshness-http
title: grafana checkpoint freshness http remediation
task_id: grafana-checkpoint-freshness-http
created_at: '2026-05-26T11:03:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Moved control-plane checkpoint freshness panel 892 to HTTP-backed persisted
  checkpoint evidence, added /ops/control-plane/checkpoint-freshness endpoint, wired
  checkpoint port into health/quarantine backend, and updated live-audit/test contracts.
---

# Episodic summary

## Task

- Title: grafana checkpoint freshness http remediation

## Outcome

- Moved control-plane checkpoint freshness panel 892 to HTTP-backed persisted checkpoint evidence, added /ops/control-plane/checkpoint-freshness endpoint, wired checkpoint port into health/quarantine backend, and updated live-audit/test contracts.

## Lessons learned

- Replace with durable follow-up if needed
