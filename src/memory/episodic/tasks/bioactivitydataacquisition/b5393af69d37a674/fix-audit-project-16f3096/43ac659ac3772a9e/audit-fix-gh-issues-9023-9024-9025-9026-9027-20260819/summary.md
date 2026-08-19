---
record_id: audit-fix-gh-issues-9023-9024-9025-9026-9027-20260819
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 3b72a77dbce9d14a08674b92b81b91340a28f1e0
branch: fix/audit-project-16f3096
worktree_id: b5393af69d37a674
task_id: audit-fix-gh-issues-9023-9024-9025-9026-9027-20260819
actor:
  runtime: codex
  agent: codex
  model: null
created_at: '2026-08-19T09:50:06.537233+00:00'
source_refs:
- scripts/engineering/repo/branch_cleanup.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: ee5ad7fdca1fa247710c598addc3aa9e4f0b2f2d54b6f1caa32e472ad26516cc
id: audit-fix-gh-issues-9023-9024-9025-9026-9027-20260819
title: Audit and correct GitHub issues 9023 9024 9025 9026 9027
ttl_days: 14
confidence: episodic
summary: 'Audited and corrected issues 9023/9024/9025/9026/9027: refreshed GitHub
  state, clarified remote read-only semantics, SHA drift and reachability gates, fresh-main
  replay rules, archive-tag tooling limits, and deferred local head deletion to 9016.
  Verified 106 branches, all 23 candidates present, 0 open PRs, 20 linked PRs closed
  unmerged, and 0/21 non-snapshot tips reachable from current main.'
---

# Episodic summary

## Task

- Title: Audit and correct GitHub issues 9023 9024 9025 9026 9027

## Outcome

- Audited and corrected issues 9023/9024/9025/9026/9027: refreshed GitHub state, clarified remote read-only semantics, SHA drift and reachability gates, fresh-main replay rules, archive-tag tooling limits, and deferred local head deletion to 9016. Verified 106 branches, all 23 candidates present, 0 open PRs, 20 linked PRs closed unmerged, and 0/21 non-snapshot tips reachable from current main.

## Lessons learned

- Replace with durable follow-up if needed
