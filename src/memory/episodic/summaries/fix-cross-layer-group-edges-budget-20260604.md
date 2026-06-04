---
id: fix-cross-layer-group-edges-budget-20260604
title: Fix cross-layer group edge budget regression
task_id: fix-cross-layer-group-edges-budget-20260604
created_at: '2026-06-04T15:01:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py::test_cross_layer_group_edges_total_budget
summary: Investigated reported cross_layer_group_edges_total=345 budget failure. Current
  dependency snapshot returns cross_layer_group_edges_total=343 with 2130 scanned
  modules, below budget 344; targeted pytest tests/architecture/test_regression_metrics.py::test_cross_layer_group_edges_total_budget
  passes. No repo code changes made and no budget increase performed.
---

# Episodic summary

## Task

- Title: Fix cross-layer group edge budget regression

## Outcome

- Investigated reported cross_layer_group_edges_total=345 budget failure. Current dependency snapshot returns cross_layer_group_edges_total=343 with 2130 scanned modules, below budget 344; targeted pytest tests/architecture/test_regression_metrics.py::test_cross_layer_group_edges_total_budget passes. No repo code changes made and no budget increase performed.

## Lessons learned

- Replace with durable follow-up if needed
