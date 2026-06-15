---
id: fix-clirunner-mix-stderr-compat
title: Fix CliRunner mix_stderr compatibility failure
task_id: fix-clirunner-mix-stderr-compat
created_at: '2026-06-15T15:30:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Made lineage CLI test fixture feature-detect CliRunner.mix_stderr so the
  suite works with Click 8.1 and 8.3, and verified the targeted test file passes in
  both Linux and .venv-win environments.
---

# Episodic summary

## Task

- Title: Fix CliRunner mix_stderr compatibility failure

## Outcome

- Made lineage CLI test fixture feature-detect CliRunner.mix_stderr so the suite works with Click 8.1 and 8.3, and verified the targeted test file passes in both Linux and .venv-win environments.

## Lessons learned

- Replace with durable follow-up if needed
