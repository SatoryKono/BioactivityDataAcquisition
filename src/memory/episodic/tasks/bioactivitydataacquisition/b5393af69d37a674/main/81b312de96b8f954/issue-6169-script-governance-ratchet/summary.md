---
record_id: issue-6169-script-governance-ratchet
record_type: working
repo_id: bioactivitydataacquisition
git_commit: ed8f96525b8e95f813ff0d48bf79efbf41fdd998
branch: main
worktree_id: b5393af69d37a674
task_id: issue-6169-script-governance-ratchet
actor:
  runtime: codex
  agent: py-debug-bot
  model: gpt-5
created_at: '2026-08-04T08:04:55.155583+00:00'
source_refs:
- reports/quality/debt-governance-gates.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 9da8e5948a0322c3d1bbcfa1ef27203354d428a70fa861fba1d99823a8c7482c
id: issue-6169-script-governance-ratchet
title: Fix issue 6169 script governance ratchet mismatch
ttl_days: 14
confidence: episodic
summary: 'DBG-001 confirmed stale generated debt governance artifacts: live scripts
  manifest and closeout outcome had 5 zero-reference rows while debt-governance-gates
  recorded 6. Regenerated canonical JSON/Markdown; current decreased to 5, limit remained
  15, all 7 closeout tests and gate checks passed.'
---

# Episodic summary

## Task

- Title: Fix issue 6169 script governance ratchet mismatch

## Outcome

- DBG-001 confirmed stale generated debt governance artifacts: live scripts manifest and closeout outcome had 5 zero-reference rows while debt-governance-gates recorded 6. Regenerated canonical JSON/Markdown; current decreased to 5, limit remained 15, all 7 closeout tests and gate checks passed.

## Lessons learned

- Replace with durable follow-up if needed
