---
record_id: issue-9629
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 077996c43947f641ec9d63089487d2c6bd6c9865
branch: fix/wave-c-9629
worktree_id: 1dbd65fe4381a8c1
task_id: issue-9629
actor:
  runtime: codex
  agent: py-config-bot
  model: gpt-5
created_at: '2026-08-25T18:33:59.530331+00:00'
source_refs:
- scripts/engineering/qa/refresh_governance_artifacts.py
- configs/quality/assertless_ratchet.yaml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 753729d04f9ab8c48f11cc4b9f6c543943d241c99de1fa52bcd26ddfb426e7e9
id: issue-9629
title: Governance regen hygiene without new YAML registries
ttl_days: 14
confidence: episodic
summary: Unified the existing governance refresh/check path, made it fail closed,
  added atomic LF scorecard sync and regression tests, documented the coupled command,
  and lowered the assertless ceiling from 102 to the measured 87 without adding registries.
  Final shared artifact drift remains assigned to issue 9647.
---

# Episodic summary

## Task

- Title: Governance regen hygiene without new YAML registries

## Outcome

- Unified the existing governance refresh/check path, made it fail closed, added atomic LF scorecard sync and regression tests, documented the coupled command, and lowered the assertless ceiling from 102 to the measured 87 without adding registries. Final shared artifact drift remains assigned to issue 9647.

## Lessons learned

- Replace with durable follow-up if needed
