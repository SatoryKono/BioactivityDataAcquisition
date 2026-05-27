---
id: grafana-runtime-dashboard-audit-20260527
title: Audit Grafana dashboard 2 Runtime sections
task_id: grafana-runtime-dashboard-audit-20260527
created_at: '2026-05-27T06:06:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
summary: Audited Grafana dashboard 2 Runtime target sections Localize, Escalate, and
  Tracing-only Log Hygiene from grafana/dashboards/bioetl-runtime.json. Found a definite
  nested collapsed-row layout overlap between Localize panels 256 and 241, query semantics
  risks from max_over_time on counters for range panels, high-cardinality raw message
  grouping in Loki warning top events, weak Loki table formatting, freshness handoff
  mismatch with shipped fixed-window condition-summary guidance, and overall UX/design
  refactoring opportunities. No files were edited.
---

# Episodic summary

## Task

- Title: Audit Grafana dashboard 2 Runtime sections

## Outcome

- Audited Grafana dashboard 2 Runtime target sections Localize, Escalate, and Tracing-only Log Hygiene from grafana/dashboards/bioetl-runtime.json. Found a definite nested collapsed-row layout overlap between Localize panels 256 and 241, query semantics risks from max_over_time on counters for range panels, high-cardinality raw message grouping in Loki warning top events, weak Loki table formatting, freshness handoff mismatch with shipped fixed-window condition-summary guidance, and overall UX/design refactoring opportunities. No files were edited.

## Lessons learned

- Replace with durable follow-up if needed
