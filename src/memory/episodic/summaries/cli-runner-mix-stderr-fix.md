---
id: cli-runner-mix-stderr-fix
title: Fix CliRunner mix_stderr compatibility
task_id: cli-runner-mix-stderr-fix
created_at: '2026-05-06T13:34:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/commands/test_run_manifest_commands.py
summary: Removed obsolete mix_stderr usage from run manifest CLI tests and added missing
  zero-fallbacks to control-plane Grafana summary panels for Replay / Resume Blockers
  and Replay Lag Seconds.
---

# Episodic summary

## Task

- Title: Fix CliRunner mix_stderr compatibility

## Outcome

- Removed obsolete mix_stderr usage from run manifest CLI tests and added missing zero-fallbacks to control-plane Grafana summary panels for Replay / Resume Blockers and Replay Lag Seconds.

## Lessons learned

- Replace with durable follow-up if needed
