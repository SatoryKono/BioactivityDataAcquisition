---
id: bioetl-dashboard-audit-issues-close-20260531
title: Close dashboard audit issues 4840 4843 4852 4853 4854
task_id: bioetl-dashboard-audit-issues-close-20260531
created_at: '2026-05-31T17:46:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/observability/dashboard-audit-20260531/live-panel-audit-expanded.json
summary: 'Implemented dashboard audit issue workstream. Closed GitHub issues #4840,
  #4852, #4853, and #4854 with validation comments. Left #4843 open with blocker comment
  because Grafana render API still returns HTTP 500 and Playwright expanded-row fallback
  requires host Chromium shared libraries that cannot be installed without interactive
  sudo. Code changes include Windows-path-tolerant checkpoint manifest-index resolution,
  expanded live panel audit generation for all shipped Prometheus/HTTP/Loki/Tempo
  targets, per-panel failure isolation, Overview Alert/SLO triage row backed by Prometheus
  ALERTS, docs sync, and module coverage inventory refresh.'
---

# Episodic summary

## Task

- Title: Close dashboard audit issues 4840 4843 4852 4853 4854

## Outcome

- Implemented dashboard audit issue workstream. Closed GitHub issues #4840, #4852, #4853, and #4854 with validation comments. Left #4843 open with blocker comment because Grafana render API still returns HTTP 500 and Playwright expanded-row fallback requires host Chromium shared libraries that cannot be installed without interactive sudo. Code changes include Windows-path-tolerant checkpoint manifest-index resolution, expanded live panel audit generation for all shipped Prometheus/HTTP/Loki/Tempo targets, per-panel failure isolation, Overview Alert/SLO triage row backed by Prometheus ALERTS, docs sync, and module coverage inventory refresh.

## Lessons learned

- Replace with durable follow-up if needed
