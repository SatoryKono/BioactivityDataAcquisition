---
id: fix-retirement-candidate-triage-main-entrypoint-20260617
title: Fix retirement candidate triage for bioetl.__main__
task_id: fix-retirement-candidate-triage-main-entrypoint-20260617
created_at: '2026-06-17T09:20:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/retirement_candidate_triage.yaml
- scripts/engineering/qa/report_dead_code_inventory.py
- reports/quality/dead-code-inventory.json
- reports/quality/dead-code-inventory.md
- tests/architecture/test_retirement_candidate_triage.py
summary: Classified src/bioetl/__main__.py as the retained python -m bioetl module
  entrypoint without increasing the zero-untriaged budget, refreshed dead-code inventory
  artifacts, and verified the retirement triage architecture tests.
---

# Episodic summary

## Task

- Title: Fix retirement candidate triage for bioetl.__main__

## Outcome

- Classified src/bioetl/__main__.py as the retained python -m bioetl module entrypoint without increasing the zero-untriaged budget, refreshed dead-code inventory artifacts, and verified the retirement triage architecture tests.

## Lessons learned

- Replace with durable follow-up if needed
