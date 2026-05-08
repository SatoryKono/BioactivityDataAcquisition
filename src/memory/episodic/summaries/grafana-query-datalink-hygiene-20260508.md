---
id: grafana-query-datalink-hygiene-20260508
title: Remove empty shipped dataLinks containers from dashboard panels
task_id: grafana-query-datalink-hygiene-20260508
created_at: '2026-05-08T11:05:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed empty options.dataLinks export-noise from Runtime, Data Quality,
  and Provider Health panels and added a generic dashboard-links contract test so
  shipped dashboards cannot carry empty panel dataLinks arrays.
---

# Episodic summary

## Task

- Title: Remove empty shipped dataLinks containers from dashboard panels

## Outcome

- Removed empty options.dataLinks export-noise from Runtime, Data Quality, and Provider Health panels and added a generic dashboard-links contract test so shipped dashboards cannot carry empty panel dataLinks arrays.

## Lessons learned

- Replace with durable follow-up if needed
