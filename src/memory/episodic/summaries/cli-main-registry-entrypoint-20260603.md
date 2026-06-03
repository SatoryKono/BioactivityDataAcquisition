---
id: cli-main-registry-entrypoint-20260603
title: Fix CLI main registry entrypoint contract
task_id: cli-main-registry-entrypoint-20260603
created_at: '2026-06-03T06:39:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/main.py
summary: 'Updated src/bioetl/interfaces/cli/main.py so canonical main() passes cli(obj=_build_main_registry()),
  and synced the stale unit expectation in tests/unit/interfaces/cli/test_cli_commands_basic.py.
  Targeted registry/CLI tests passed. Full coverage-verify refresh for reports/quality/module-coverage-inventory.json
  was blocked by unrelated worktree drift: untracked runtime-builder files and existing
  formatting/workflow test failures outside this change.'
---

# Episodic summary

## Task

- Title: Fix CLI main registry entrypoint contract

## Outcome

- Updated src/bioetl/interfaces/cli/main.py so canonical main() passes cli(obj=_build_main_registry()), and synced the stale unit expectation in tests/unit/interfaces/cli/test_cli_commands_basic.py. Targeted registry/CLI tests passed. Full coverage-verify refresh for reports/quality/module-coverage-inventory.json was blocked by unrelated worktree drift: untracked runtime-builder files and existing formatting/workflow test failures outside this change.

## Lessons learned

- Replace with durable follow-up if needed
