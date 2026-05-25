---
id: fix-grafana-explore-traces-tooltip-case-20260525
title: Fix Grafana Explore Traces tooltip traced-run wording
task_id: fix-grafana-explore-traces-tooltip-case-20260525
created_at: '2026-05-25T10:36:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-dq-v2.json
summary: Updated bioetl-dq-v2 Explore Traces navigation tooltip to include the exact
  traced-run-only phrase Available only for traced runs, aligning it with shipped
  dashboard link integration tests and the other dashboards.
---

# Episodic summary

## Task

- Title: Fix Grafana Explore Traces tooltip traced-run wording

## Outcome

- Updated bioetl-dq-v2 Explore Traces navigation tooltip to include the exact traced-run-only phrase Available only for traced runs, aligning it with shipped dashboard link integration tests and the other dashboards.

## Lessons learned

- Tooltip wording is case-sensitive in Grafana navigation link contract tests; keep shipped dashboard tooltip phrases byte-aligned with the asserted operator language.
