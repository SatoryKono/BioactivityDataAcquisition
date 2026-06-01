---
id: dashboard-variable-handoff-check-20260601
title: Check Grafana dashboard Workflow Pipeline Run Type Run ID handoffs
task_id: dashboard-variable-handoff-check-20260601
created_at: '2026-06-01T18:30:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards
summary: Checked Grafana dashboard variable handoff semantics. Machine-readable panel.links
  and existing contract tests pass for primary dashboard handoffs, but visible HTML
  navigation bus anchors in panel id=1000 on primary dashboards omit var-workflow
  and var-run_id, so operator clicks on the visible bus lose Workflow and Run ID.
  Silver Reject Explorer and Alerts/SLO omissions are intentional boundary exceptions.
---

# Episodic summary

## Task

- Title: Check Grafana dashboard Workflow Pipeline Run Type Run ID handoffs

## Outcome

- Checked Grafana dashboard variable handoff semantics. Machine-readable panel.links and existing contract tests pass for primary dashboard handoffs, but visible HTML navigation bus anchors in panel id=1000 on primary dashboards omit var-workflow and var-run_id, so operator clicks on the visible bus lose Workflow and Run ID. Silver Reject Explorer and Alerts/SLO omissions are intentional boundary exceptions.

## Lessons learned

- Replace with durable follow-up if needed
