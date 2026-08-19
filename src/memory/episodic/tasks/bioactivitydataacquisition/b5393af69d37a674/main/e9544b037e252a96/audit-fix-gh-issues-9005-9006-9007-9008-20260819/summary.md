---
record_id: audit-fix-gh-issues-9005-9006-9007-9008-20260819
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 21dcaa936808fba3e3368136b8865db180ee36e1
branch: main
worktree_id: b5393af69d37a674
task_id: audit-fix-gh-issues-9005-9006-9007-9008-20260819
actor:
  runtime: codex
  agent: codex
  model: null
created_at: '2026-08-19T11:08:15.892351+00:00'
source_refs:
- scripts/ai/sync/governance.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 07daeff2df453d572a6daa1736e35e5931c0fdc4e6d02b9f2033f6387563786c
id: audit-fix-gh-issues-9005-9006-9007-9008-20260819
title: Audit and correct GitHub issues 9005 9006 9007 9008
ttl_days: 14
confidence: episodic
summary: 'Corrected GitHub issues 9005-9008 against main 21dcaa936808: made retention
  count time-bound and count-neutral with a fresh 19-candidate owner gate; marked
  skill-mirror and prompt-link findings resolved with green checks; corrected issue
  9007 root cause from CODEX-RUNTIME content to generic-normalizer behavior and documented
  dedicated runtime-map normalization plus doctor enforcement. No prune apply or repository
  source mutation.'
---

# Episodic summary

## Task

- Title: Audit and correct GitHub issues 9005 9006 9007 9008

## Outcome

- Corrected GitHub issues 9005-9008 against main 21dcaa936808: made retention count time-bound and count-neutral with a fresh 19-candidate owner gate; marked skill-mirror and prompt-link findings resolved with green checks; corrected issue 9007 root cause from CODEX-RUNTIME content to generic-normalizer behavior and documented dedicated runtime-map normalization plus doctor enforcement. No prune apply or repository source mutation.

## Lessons learned

- Replace with durable follow-up if needed
