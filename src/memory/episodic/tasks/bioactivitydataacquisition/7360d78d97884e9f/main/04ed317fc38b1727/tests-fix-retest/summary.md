---
record_id: tests-fix-retest
record_type: working
repo_id: bioactivitydataacquisition
git_commit: a739c347eb0a8ce101392ac09c808ab8d2ae9e93
branch: main
worktree_id: 7360d78d97884e9f
task_id: tests-fix-retest
actor:
  runtime: grok
  agent: py-test-bot
  model: grok-4
created_at: '2026-08-20T23:48:29.517188+00:00'
source_refs:
- docs/00-project/ai/prompts/library/tests/fix-retest-loop.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 2f158ecd07e7e72f2557da237b9efdf28f09cfad084571765c241f511459f3df
id: tests-fix-retest
title: Fixed 9 unit failures on main SHA 343a6b349b
ttl_days: 14
confidence: episodic
summary: 'Reproduced CI unit failures on origin/main@343a6b349b and fixed 4 root causes
  (debt-governance re-export, prometheus inventory 170, CompositeValidator wrapper,
  health-server IdentityScope/table-shape tests). 9 previously failed nodeids and
  122 tests in touched files passed. Full unit-fast NOT_PROVEN locally. Residual LFS
  #9040 and out-of-lane security/integration/contract.'
---

# Episodic summary

## Task

- Title: Fixed 9 unit failures on main SHA 343a6b349b

## Outcome

- Reproduced CI unit failures on origin/main@343a6b349b and fixed 4 root causes (debt-governance re-export, prometheus inventory 170, CompositeValidator wrapper, health-server IdentityScope/table-shape tests). 9 previously failed nodeids and 122 tests in touched files passed. Full unit-fast NOT_PROVEN locally. Residual LFS #9040 and out-of-lane security/integration/contract.

## Lessons learned

- Replace with durable follow-up if needed
