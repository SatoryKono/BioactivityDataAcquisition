---
record_id: docs-nav-growth-persistent-20260730
record_type: working
repo_id: bioactivitydataacquisition
git_commit: e00d438b57e6912e88d4393c47465c08240c1f6d
branch: main
worktree_id: ccd98afae0adb4ee
task_id: docs-nav-growth-persistent-20260730
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T06:32:58.649346+00:00'
source_refs:
- mkdocs.yml
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: eea32f9946b54538e9519f727c4a3abe229d7261eae75d3ac24ef8ed11371758
id: docs-nav-growth-persistent-20260730
title: Persist docs nav growth fix without raising baseline
ttl_days: 14
confidence: episodic
summary: Restored the two publication-appropriate mkdocs nav entries after a concurrent
  workspace rewrite removed them. Confirmed mkdocs.yml is the manual publication SSOT
  with no generator. Not-in-nav is 297 against unchanged baseline 297 and all 24 guardrail
  tests pass. Docs drift and links pass. Unrelated pre-existing Codex/Junie mirror
  parity has 24 drift entries and was not synced.
---

# Episodic summary

## Task

- Title: Persist docs nav growth fix without raising baseline

## Outcome

- Restored the two publication-appropriate mkdocs nav entries after a concurrent workspace rewrite removed them. Confirmed mkdocs.yml is the manual publication SSOT with no generator. Not-in-nav is 297 against unchanged baseline 297 and all 24 guardrail tests pass. Docs drift and links pass. Unrelated pre-existing Codex/Junie mirror parity has 24 drift entries and was not synced.

## Lessons learned

- Replace with durable follow-up if needed
