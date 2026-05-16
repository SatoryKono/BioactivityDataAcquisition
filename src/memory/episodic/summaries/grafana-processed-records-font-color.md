---
id: grafana-processed-records-font-color
title: Adjust Processed Records panel font and muted rows
task_id: grafana-processed-records-font-color
created_at: '2026-05-16T12:02:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Set Processed Records table cellHeight to sm across dashboards 0..5 and removed
  explicit secondary row text colors so non-primary rows inherit the ID panel/default
  table text color while bronze total, silver valid, and gold valid remain colored.
  Updated semantic regression tests and validated JSON/layout contracts.
---

# Episodic summary

## Task

- Title: Adjust Processed Records panel font and muted rows

## Outcome

- Set Processed Records table cellHeight to sm across dashboards 0..5 and removed explicit secondary row text colors so non-primary rows inherit the ID panel/default table text color while bronze total, silver valid, and gold valid remain colored. Updated semantic regression tests and validated JSON/layout contracts.

## Lessons learned

- Replace with durable follow-up if needed
