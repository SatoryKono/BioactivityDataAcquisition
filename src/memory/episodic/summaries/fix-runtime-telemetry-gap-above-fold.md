---
id: fix-runtime-telemetry-gap-above-fold
title: Fix runtime telemetry gap above-fold placement
task_id: fix-runtime-telemetry-gap-above-fold
created_at: '2026-05-22T18:35:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Resolved a false-negative in dashboard QA: the shipped Runtime Telemetry
  Gap trust marker already matched runtime dashboard docs and integration tests at
  y=23 on the first-screen evidence row, but check_dashboard_visual_semantics.py incorrectly
  required y<=22. Updated the canonical visual-semantics guard to treat y<=23 as above
  fold for trust markers, validated runtime dashboard JSON, re-ran the canonical semantics
  script, and passed targeted Grafana runtime/layout/visual-semantic/Prometheus-rules
  integration tests.'
---

# Episodic summary

## Task

- Title: Fix runtime telemetry gap above-fold placement

## Outcome

- Resolved a false-negative in dashboard QA: the shipped Runtime Telemetry Gap trust marker already matched runtime dashboard docs and integration tests at y=23 on the first-screen evidence row, but check_dashboard_visual_semantics.py incorrectly required y<=22. Updated the canonical visual-semantics guard to treat y<=23 as above fold for trust markers, validated runtime dashboard JSON, re-ran the canonical semantics script, and passed targeted Grafana runtime/layout/visual-semantic/Prometheus-rules integration tests.

## Lessons learned

- Replace with durable follow-up if needed
