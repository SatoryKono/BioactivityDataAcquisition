---
record_id: debug-ci-marker-drift
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 9c9fa5791aac29a3ec98e268670d98ebde33867c
branch: main
worktree_id: ccd98afae0adb4ee
task_id: debug-ci-marker-drift
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T15:40:16.585078+00:00'
source_refs:
- .github/workflows/tests.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 7bb9468c6bbb2927e37c76aae281a39b94e9afdc126f4d568e70b0f5adb772c2
id: debug-ci-marker-drift
title: Debug test-fast marker drift
ttl_days: 14
confidence: episodic
summary: Aligned the tests.yml test-fast marker with the canonical unit-fast marker_expression
  by excluding fs_contract; focused and adjacent architecture tests pass.
---

# Episodic summary

## Task

- Title: Debug test-fast marker drift

## Outcome

- Aligned the tests.yml test-fast marker with the canonical unit-fast marker_expression by excluding fs_contract; focused and adjacent architecture tests pass.

## Lessons learned

- Replace with durable follow-up if needed
