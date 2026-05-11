---
id: provider-health-variable-canonicalize
title: Canonicalize Provider Health provider variable source
task_id: provider-health-variable-canonicalize
created_at: '2026-05-11T14:11:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-provider-health-v2.json
summary: Switched the Provider Health provider selector from a __name__ regex over
  raw health-check counters to the canonical provider-universe recording rule and
  updated the Grafana contract test accordingly.
---

# Episodic summary

## Task

- Title: Canonicalize Provider Health provider variable source

## Outcome

- Switched the Provider Health provider selector from a __name__ regex over raw health-check counters to the canonical provider-universe recording rule and updated the Grafana contract test accordingly.

## Lessons learned

- Replace with durable follow-up if needed
