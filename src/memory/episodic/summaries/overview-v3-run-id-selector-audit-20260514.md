---
id: overview-v3-run-id-selector-audit-20260514
title: Audit Overview v3 Run ID selector
task_id: overview-v3-run-id-selector-audit-20260514
created_at: '2026-05-14T07:51:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-overview-v3.json
summary: Audited Overview v3 Run ID selector. Found the selector was HTTP-backed and
  exact selection worked through identity-table, but the Grafana variable had empty
  current/options and the control-plane list response lacked a no-selection sentinel,
  risking implicit first-run selection. Updated Overview v3 run_id current/options
  to '-', added '-' sentinel to control-plane filter-options list responses, normalized
  '-' as unselected in identity-table, synchronized selector/navigation docs and tests,
  and validated targeted Grafana/backend contracts. Live backend on 127.0.0.1:8081
  confirmed selecting a concrete run_id resolves selected_run_id; the already-running
  service was not restarted so its list endpoint did not yet include the new '-' sentinel.
---

# Episodic summary

## Task

- Title: Audit Overview v3 Run ID selector

## Outcome

- Audited Overview v3 Run ID selector. Found the selector was HTTP-backed and exact selection worked through identity-table, but the Grafana variable had empty current/options and the control-plane list response lacked a no-selection sentinel, risking implicit first-run selection. Updated Overview v3 run_id current/options to '-', added '-' sentinel to control-plane filter-options list responses, normalized '-' as unselected in identity-table, synchronized selector/navigation docs and tests, and validated targeted Grafana/backend contracts. Live backend on 127.0.0.1:8081 confirmed selecting a concrete run_id resolves selected_run_id; the already-running service was not restarted so its list endpoint did not yet include the new '-' sentinel.

## Lessons learned

- Replace with durable follow-up if needed
