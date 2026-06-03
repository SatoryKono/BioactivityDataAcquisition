---
id: cli-list-pipelines-import-timeout
title: Debug CLI list-pipelines import timeout
task_id: cli-list-pipelines-import-timeout
created_at: '2026-06-03T09:40:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/config.py
- src/bioetl/composition/config_catalog.py
summary: Fixed unit CLI config list-pipelines timeout by moving the command to a lightweight
  composition config-catalog seam that scans non-composite configs/entities YAML names
  instead of bootstrapping ConfigService/provider registrations; added regression
  coverage and refreshed module coverage/dependency/test-governance artifacts. Also
  wrapped run_manifest module docstring to restore whole-src ruff zero budget.
---

# Episodic summary

## Task

- Title: Debug CLI list-pipelines import timeout

## Outcome

- Fixed unit CLI config list-pipelines timeout by moving the command to a lightweight composition config-catalog seam that scans non-composite configs/entities YAML names instead of bootstrapping ConfigService/provider registrations; added regression coverage and refreshed module coverage/dependency/test-governance artifacts. Also wrapped run_manifest module docstring to restore whole-src ruff zero budget.

## Lessons learned

- Replace with durable follow-up if needed
