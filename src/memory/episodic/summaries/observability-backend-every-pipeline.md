---
id: observability-backend-every-pipeline
title: Enable observability backend check for every pipeline CLI
task_id: observability-backend-every-pipeline
created_at: '2026-06-01T18:14:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/domains/health/observability_backend_runtime.py
summary: Added required observability capability probes to pipeline CLI entrypoints
  so run, run-all, run-composite, and workflow commands now validate control-plane
  observability endpoints and trigger stale-backend restart through the shared detached
  Quarantine Explorer ensure path. Added probe-path builder tests, CLI command assertions,
  refreshed module coverage inventory, and passed targeted pytest and ruff validation.
---

# Episodic summary

## Task

- Title: Enable observability backend check for every pipeline CLI

## Outcome

- Added required observability capability probes to pipeline CLI entrypoints so run, run-all, run-composite, and workflow commands now validate control-plane observability endpoints and trigger stale-backend restart through the shared detached Quarantine Explorer ensure path. Added probe-path builder tests, CLI command assertions, refreshed module coverage inventory, and passed targeted pytest and ruff validation.

## Lessons learned

- Replace with durable follow-up if needed
