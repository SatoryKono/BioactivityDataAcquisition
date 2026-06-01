---
id: dashboard-audit-issues-4941-4949-implementation
title: Dashboard link contract regression fix
task_id: dashboard-audit-issues-4941-4949-implementation
created_at: '2026-06-01T16:57:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Resolved Grafana dashboard link contract regressions after Alerts/SLO and
  Silver Reject Explorer changes. Alerts/SLO is now first-class in navigation contracts
  but does not own primary run_id. Silver Reject Explorer no longer declares or exports
  primary run_id; inbound primary run_id maps only to quarantine_run_id. Updated dashboard
  JSON, navigation contract, docs, and integration/unit tests. Validated dashboard
  links, Grafana config, unit dashboard tooling, ruff, inventory, and live audit.
---

# Episodic summary

## Task

- Title: Dashboard link contract regression fix

## Outcome

- Resolved Grafana dashboard link contract regressions after Alerts/SLO and Silver Reject Explorer changes. Alerts/SLO is now first-class in navigation contracts but does not own primary run_id. Silver Reject Explorer no longer declares or exports primary run_id; inbound primary run_id maps only to quarantine_run_id. Updated dashboard JSON, navigation contract, docs, and integration/unit tests. Validated dashboard links, Grafana config, unit dashboard tooling, ruff, inventory, and live audit.

## Lessons learned

- Replace with durable follow-up if needed
