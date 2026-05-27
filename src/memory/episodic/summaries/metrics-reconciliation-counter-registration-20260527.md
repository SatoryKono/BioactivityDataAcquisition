---
id: metrics-reconciliation-counter-registration-20260527
title: Fix reconciliation Prometheus counter registration
task_id: metrics-reconciliation-counter-registration-20260527
created_at: '2026-05-27T05:36:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/observability/prometheus_metric_registries.py
summary: Registered workflow reconciliation row counters in Prometheus metric definitions
  and runtime registry, updated the metric count ratchet, and made PrometheusMetrics
  dispatch no-label metrics directly while rejecting unexpected labels. Targeted observability
  and workflow reconciliation tests passed.
---

# Episodic summary

## Task

- Title: Fix reconciliation Prometheus counter registration

## Outcome

- Registered workflow reconciliation row counters in Prometheus metric definitions and runtime registry, updated the metric count ratchet, and made PrometheusMetrics dispatch no-label metrics directly while rejecting unexpected labels. Targeted observability and workflow reconciliation tests passed.

## Lessons learned

- Replace with durable follow-up if needed
