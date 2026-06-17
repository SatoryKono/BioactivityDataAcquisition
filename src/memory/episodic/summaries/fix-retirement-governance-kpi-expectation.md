---
id: fix-retirement-governance-kpi-expectation
title: Fix retirement governance KPI expectation
task_id: fix-retirement-governance-kpi-expectation
created_at: '2026-06-17T09:19:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_quality_debt_scorecard.py
summary: 'Restored src/bioetl/__main__.py as a classified retain_module_entrypoint
  repo-wide zero-import candidate so retirement governance metrics match the live
  dead-code inventory across environments. Regenerated dead-code inventory at 10 classified
  candidates with 0 untriaged, restored scorecard counts to the intended #5278 ratchet
  from 11 to 10, and verified the targeted debt scorecard and retirement triage architecture
  tests pass. Debt budgets were not raised above the reviewed #5278 baseline.'
---

# Episodic summary

## Task

- Title: Fix retirement governance KPI expectation

## Outcome

- Restored src/bioetl/__main__.py as a classified retain_module_entrypoint repo-wide zero-import candidate so retirement governance metrics match the live dead-code inventory across environments. Regenerated dead-code inventory at 10 classified candidates with 0 untriaged, restored scorecard counts to the intended #5278 ratchet from 11 to 10, and verified the targeted debt scorecard and retirement triage architecture tests pass. Debt budgets were not raised above the reviewed #5278 baseline.

## Lessons learned

- Replace with durable follow-up if needed
