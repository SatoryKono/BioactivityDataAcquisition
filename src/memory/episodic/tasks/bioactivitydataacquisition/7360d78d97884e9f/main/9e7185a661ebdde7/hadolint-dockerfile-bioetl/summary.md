---
record_id: hadolint-dockerfile-bioetl
record_type: working
repo_id: bioactivitydataacquisition
git_commit: eea23e476a4749bfd09188c2b6a3a5a8a893f3cb
branch: main
worktree_id: 7360d78d97884e9f
task_id: hadolint-dockerfile-bioetl
actor:
  runtime: cursor
  agent: cursor-grok-4.6
  model: null
created_at: '2026-08-21T17:30:22.710855+00:00'
source_refs:
- Dockerfile.bioetl
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: d549c10f8500259fabab780095ab9b0c84975ec6311b0aff39b401541bbd10f3
id: hadolint-dockerfile-bioetl
title: Fix Hadolint findings in Dockerfile.bioetl
ttl_days: 14
confidence: episodic
summary: Dockerfile.bioetl now pins uv on the pip install line, sets bash pipefail
  SHELL in both stages, uses USER 999:999, and JSON HEALTHCHECK CMD. hadolint --failure-threshold
  info passes.
---

# Episodic summary

## Task

- Title: Fix Hadolint findings in Dockerfile.bioetl

## Outcome

- Dockerfile.bioetl now pins uv on the pip install line, sets bash pipefail SHELL in both stages, uses USER 999:999, and JSON HEALTHCHECK CMD. hadolint --failure-threshold info passes.

## Lessons learned

- Replace with durable follow-up if needed
