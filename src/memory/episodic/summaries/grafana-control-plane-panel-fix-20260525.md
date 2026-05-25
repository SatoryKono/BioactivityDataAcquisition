---
id: grafana-control-plane-panel-fix-20260525
title: Fix missing Grafana control-plane read panel
task_id: grafana-control-plane-panel-fix-20260525
created_at: '2026-05-25T10:32:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/test_grafana_layout_and_metadata.py
summary: 'Updated stale Grafana integration expectation: test_grafana_layout_and_metadata
  still referenced the old control-plane ratio panel title without the Severity suffix,
  while the shipped dashboard and other Grafana tests already use the canonical ''Monitor:
  GLOBAL Control-Plane Read Failure Ratio Severity'' title. Verified the targeted
  nodeid passes after aligning the test.'
---

# Episodic summary

## Task

- Title: Fix missing Grafana control-plane read panel

## Outcome

- Updated stale Grafana integration expectation: test_grafana_layout_and_metadata still referenced the old control-plane ratio panel title without the Severity suffix, while the shipped dashboard and other Grafana tests already use the canonical 'Monitor: GLOBAL Control-Plane Read Failure Ratio Severity' title. Verified the targeted nodeid passes after aligning the test.

## Lessons learned

- Replace with durable follow-up if needed
