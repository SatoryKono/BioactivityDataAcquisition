---
record_id: issue-6776-vcr-slimming
record_type: working
repo_id: bioactivitydataacquisition
git_commit: a1811ade77bc5dcd2e63e371d965227915cb38df
branch: fix/issue-6776-vcr-slimming
worktree_id: ccd98afae0adb4ee
task_id: issue-6776-vcr-slimming
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T16:07:24.473034+00:00'
source_refs:
- scripts/engineering/qa/report_vcr_metadata_catalog.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: a491e530bdc4180810a7439fc31875e68477a618085ae09ec86549a866ac1bb3
id: issue-6776-vcr-slimming
title: Slim oversized ChEMBL VCR cassettes
ttl_days: 14
confidence: episodic
summary: Removed orphan oversized ChEMBL cassette and sidecar, retired stale catalog
  alias, added alias reachability regression, refreshed VCR metadata/census, and passed
  all VCR governance checks.
---

# Episodic summary

## Task

- Title: Slim oversized ChEMBL VCR cassettes

## Outcome

- Removed orphan oversized ChEMBL cassette and sidecar, retired stale catalog alias, added alias reachability regression, refreshed VCR metadata/census, and passed all VCR governance checks.

## Lessons learned

- Replace with durable follow-up if needed
