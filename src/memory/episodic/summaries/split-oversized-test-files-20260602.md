---
id: split-oversized-test-files-20260602
title: Split oversized test files under 2000 LOC
task_id: split-oversized-test-files-20260602
created_at: '2026-06-02T09:18:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Split the oversized CLI and Grafana dashboard tooling test files into focused
  sibling modules without changing covered behavior. Moved run/run_all CLI tests into
  tests/unit/interfaces/cli/test_cli_run_commands.py and moved Grafana preflight/cycle/report
  tests into tests/unit/scripts/ops/observability/test_grafana_dashboard_audit_cycle.py,
  leaving the original files under the 2000 LOC structural-debt cap. Verified LOC
  counts, ran ruff on the touched test modules, and passed targeted pytest including
  the structural debt guard.
---

# Episodic summary

## Task

- Title: Split oversized test files under 2000 LOC

## Outcome

- Split the oversized CLI and Grafana dashboard tooling test files into focused sibling modules without changing covered behavior. Moved run/run_all CLI tests into tests/unit/interfaces/cli/test_cli_run_commands.py and moved Grafana preflight/cycle/report tests into tests/unit/scripts/ops/observability/test_grafana_dashboard_audit_cycle.py, leaving the original files under the 2000 LOC structural-debt cap. Verified LOC counts, ran ruff on the touched test modules, and passed targeted pytest including the structural debt guard.

## Lessons learned

- Replace with durable follow-up if needed
