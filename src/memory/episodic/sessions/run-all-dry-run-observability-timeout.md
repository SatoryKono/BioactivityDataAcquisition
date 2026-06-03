---
id: run-all-dry-run-observability-timeout
title: Debug run-all dry-run observability timeout
task_id: run-all-dry-run-observability-timeout
created_at: '2026-06-03T11:00:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/test_run_all_command.py
summary: Active task session context.
query: test_run_all_dry_run_mode run-all dry-run ensure_observability_backend_started
  urlopen timeout observability_backend_runtime
---

# Session note

## Task

- Title: Debug run-all dry-run observability timeout
- Retrieval query: test_run_all_dry_run_mode run-all dry-run ensure_observability_backend_started urlopen timeout observability_backend_runtime

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
