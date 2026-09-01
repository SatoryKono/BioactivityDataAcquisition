---
record_id: sync-master20260831-7-governance-drift-20260901
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 7380ba10ff54408457c8d7c469b3557428731c9f
branch: codex/sync-master20260831-7-20260901
worktree_id: 97a5b9642cf2f8c4
task_id: sync-master20260831-7-governance-drift-20260901
actor:
  runtime: codex
  agent: py-test-bot
  model: null
created_at: '2026-09-01T05:03:54.554947+00:00'
source_refs:
- reports/quality/test-governance-current.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 14d8e9307c26b093a6e7321148d058ef625d9b2140c8915a8151c5613d15f0a7
id: sync-master20260831-7-governance-drift-20260901
title: Repair test governance artifact drift
ttl_days: 14
confidence: episodic
summary: 'Repaired post-merge GitHub Actions regressions: regenerated the canonical
  test-governance snapshot, removed unsupported OSV policy flags, restored the 60-second
  default timeout, removed a duplicate timeout marker, and restored a strict case-insensitive
  MCP path assertion. Canonical governance checks, full Ruff, 48 governance tests,
  and 95 workflow/MCP/diagram tests passed; one documented Windows filesystem-performance
  test skipped.'
---

# Episodic summary

## Task

- Title: Repair test governance artifact drift

## Outcome

- Repaired post-merge GitHub Actions regressions: regenerated the canonical test-governance snapshot, removed unsupported OSV policy flags, restored the 60-second default timeout, removed a duplicate timeout marker, and restored a strict case-insensitive MCP path assertion. Canonical governance checks, full Ruff, 48 governance tests, and 95 workflow/MCP/diagram tests passed; one documented Windows filesystem-performance test skipped.

## Lessons learned

- Replace with durable follow-up if needed
