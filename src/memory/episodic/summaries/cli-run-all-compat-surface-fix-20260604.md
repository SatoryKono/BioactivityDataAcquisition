---
id: cli-run-all-compat-surface-fix-20260604
title: Restore run_all CLI compatibility exports
task_id: cli-run-all-compat-surface-fix-20260604
created_at: '2026-06-04T11:07:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Restored run_all module-level compatibility seams so _run_all_with_cli_policy
  and _run_all_callback call patchable run_all_command_flow and dispatch_cli_callback
  directly again; the two previously failing CLI unit tests now pass. Post-change
  module-coverage hash refresh was attempted, but the source-tree hash guard remained
  unstable on the current shared-drive worktree and needs separate follow-up.
---

# Episodic summary

## Task

- Title: Restore run_all CLI compatibility exports

## Outcome

- Restored run_all module-level compatibility seams so _run_all_with_cli_policy and _run_all_callback call patchable run_all_command_flow and dispatch_cli_callback directly again; the two previously failing CLI unit tests now pass. Post-change module-coverage hash refresh was attempted, but the source-tree hash guard remained unstable on the current shared-drive worktree and needs separate follow-up.

## Lessons learned

- Replace with durable follow-up if needed
