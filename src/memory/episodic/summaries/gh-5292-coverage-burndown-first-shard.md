---
id: gh-5292-coverage-burndown-first-shard
title: 'Burn down first shard of below-85 module coverage under #5244'
task_id: gh-5292-coverage-burndown-first-shard
created_at: '2026-06-17T11:09:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/module-coverage-inventory.json
- reports/quality/architecture-quality-scorecard.json
- reports/coverage/coverage.xml
summary: 'Closed GitHub issue #5292 after adding behavior-focused tests for six below-85
  modules across CLI historical replay helpers, CLI service seams, composite merge
  strategy mapping, Gold debug export rows, quarantine statistics, and structural
  policy coercion. Refreshed coverage XML, module coverage inventory, and architecture
  quality scorecard. Below-85 module count decreased from 112 to 106 while uncovered
  and unmeasured module counts remained zero. Targeted tests, ruff, module coverage
  check, architecture inventory/scorecard tests, and JSON validation passed. #5244
  remains open because 106 modules remain below 85%.'
---

# Episodic summary

## Task

- Title: Burn down first shard of below-85 module coverage under #5244

## Outcome

- Closed GitHub issue #5292 after adding behavior-focused tests for six below-85 modules across CLI historical replay helpers, CLI service seams, composite merge strategy mapping, Gold debug export rows, quarantine statistics, and structural policy coercion. Refreshed coverage XML, module coverage inventory, and architecture quality scorecard. Below-85 module count decreased from 112 to 106 while uncovered and unmeasured module counts remained zero. Targeted tests, ruff, module coverage check, architecture inventory/scorecard tests, and JSON validation passed. #5244 remains open because 106 modules remain below 85%.

## Lessons learned

- Replace with durable follow-up if needed
