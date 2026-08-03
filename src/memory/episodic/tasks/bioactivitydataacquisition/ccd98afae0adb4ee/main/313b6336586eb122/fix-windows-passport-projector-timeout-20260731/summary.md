---
record_id: fix-windows-passport-projector-timeout-20260731
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 773ad7b5145034ce18a0c3eb75b0ab475912528e
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-windows-passport-projector-timeout-20260731
actor:
  runtime: codex
  agent: py-debug-bot
  model: gpt-5
created_at: '2026-07-31T19:31:50.061488+00:00'
source_refs:
- tests/unit/scripts/docs/passports/test_passport_projector.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: a16386a71e2c5cd087c2c9f44546482240a3c901c7064505c5a9cd34488c90f4
id: fix-windows-passport-projector-timeout-20260731
title: Fix Windows passport projector timeout
ttl_days: 14
confidence: episodic
summary: Moved the slow passport environment-invariance subprocess to file-backed
  execution with a bounded child timeout and explicit slow-test timeout; validated
  directly and through the Zed runner on Windows.
---

# Episodic summary

## Task

- Title: Fix Windows passport projector timeout

## Outcome

- Moved the slow passport environment-invariance subprocess to file-backed execution with a bounded child timeout and explicit slow-test timeout; validated directly and through the Zed runner on Windows.

## Lessons learned

- Replace with durable follow-up if needed
