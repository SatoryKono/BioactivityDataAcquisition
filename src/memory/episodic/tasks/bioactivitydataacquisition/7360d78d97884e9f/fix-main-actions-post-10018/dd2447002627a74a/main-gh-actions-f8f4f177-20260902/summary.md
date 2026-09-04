---
record_id: main-gh-actions-f8f4f177-20260902
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 603167c0911bdf98893230d1fea565138f482057
branch: fix/main-actions-post-10018
worktree_id: 7360d78d97884e9f
task_id: main-gh-actions-f8f4f177-20260902
actor:
  runtime: codex
  agent: codex-primary
  model: null
created_at: '2026-09-03T09:37:10.851303+00:00'
source_refs:
- main@8b47745fa283947aa94ecf8d98032f32ba0df2fd;pr10019@6ddf375388ff88d5f3f230c5d41d5b2791253e66
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 72c2d10535d58b6719516601efbe8ab54fa8ed6785f7848c919e06f40ff01754
id: main-gh-actions-f8f4f177-20260902
title: Main GitHub Actions closeout after diagram regression
ttl_days: 14
confidence: episodic
summary: 'Verified current main 8b47745 has no failed exact-SHA runs: Tests and all
  non-publication Docker gates passed; docker-push remains pending behind required
  ghcr-publish approval and was not approved. PR 10019 head 6ddf375 has all reported
  checks passing, and the requested visual-smoke command passes locally with 6 baselines
  unchanged, but full-corpus render-diagrams is skipped because a concurrent commit
  disabled the job, so that regression is not canonically verified and the PR was
  not merged.'
---

# Episodic summary

## Task

- Title: Main GitHub Actions closeout after diagram regression

## Outcome

- Verified current main 8b47745 has no failed exact-SHA runs: Tests and all non-publication Docker gates passed; docker-push remains pending behind required ghcr-publish approval and was not approved. PR 10019 head 6ddf375 has all reported checks passing, and the requested visual-smoke command passes locally with 6 baselines unchanged, but full-corpus render-diagrams is skipped because a concurrent commit disabled the job, so that regression is not canonically verified and the PR was not merged.

## Lessons learned

- Replace with durable follow-up if needed
