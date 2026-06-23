---
id: fix-5507-cli-config-owner-seam-20260622
title: 'Fix #5507 CLI config owner seam regression'
task_id: fix-5507-cli-config-owner-seam-20260622
created_at: '2026-06-23T04:30:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/cli/config.py
summary: 'Routed CLI bootstrap DQ config loading through bioetl.composition.runtime_builders.config_access
  instead of direct infrastructure imports. Preserved the cli.config.load_dq_config_for_pipeline
  patch target and explicit configs_root propagation. Refreshed module coverage source_tree_sha256
  and architecture scorecard module coverage reference without regenerating the local
  partial coverage lane. Validation: closeout tests for 5507/5509 passed, CLI config
  unit tests passed, ruff passed, architecture scorecard/hash guard passed with WSL
  source hash skip.'
---

# Episodic summary

## Task

- Title: Fix #5507 CLI config owner seam regression

## Outcome

- Routed CLI bootstrap DQ config loading through bioetl.composition.runtime_builders.config_access instead of direct infrastructure imports. Preserved the cli.config.load_dq_config_for_pipeline patch target and explicit configs_root propagation. Refreshed module coverage source_tree_sha256 and architecture scorecard module coverage reference without regenerating the local partial coverage lane. Validation: closeout tests for 5507/5509 passed, CLI config unit tests passed, ruff passed, architecture scorecard/hash guard passed with WSL source hash skip.

## Lessons learned

- Replace with durable follow-up if needed
