---
id: fix-regression-metrics-exemption-budget-20260622
title: Fix regression metrics exemption budget
task_id: fix-regression-metrics-exemption-budget-20260622
created_at: '2026-06-22T16:46:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py
summary: Fixed regression metrics exemption budget failures without increasing debt
  budgets. Split PipelineRunContext from src/bioetl/domain/context.py into src/bioetl/domain/context_run.py
  and moved shared deterministic timestamp helpers to src/bioetl/domain/context_time.py,
  reducing context.py from 361 lines to 110 and keeping new domain modules under the
  305-line limit. The active architecture_metric_exemptions file_size_limits registry
  is empty, matching debt_scorecard baseline zero. Refreshed module-coverage inventory
  and architecture-quality-scorecard generated artifacts. Validation passed for reported
  regression metrics, file-size limits, domain context tests, module coverage/scorecard
  guards, quality debt scorecard, exemptions registry tests, YAML parse, and ruff.
---

# Episodic summary

## Task

- Title: Fix regression metrics exemption budget

## Outcome

- Fixed regression metrics exemption budget failures without increasing debt budgets. Split PipelineRunContext from src/bioetl/domain/context.py into src/bioetl/domain/context_run.py and moved shared deterministic timestamp helpers to src/bioetl/domain/context_time.py, reducing context.py from 361 lines to 110 and keeping new domain modules under the 305-line limit. The active architecture_metric_exemptions file_size_limits registry is empty, matching debt_scorecard baseline zero. Refreshed module-coverage inventory and architecture-quality-scorecard generated artifacts. Validation passed for reported regression metrics, file-size limits, domain context tests, module coverage/scorecard guards, quality debt scorecard, exemptions registry tests, YAML parse, and ruff.

## Lessons learned

- Replace with durable follow-up if needed
