---
record_id: coverage-local-uv-resolver
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 39fba14dc2f58997a0b4614f0c241a7835966d68
branch: fix/docs-ruleset-active-9800-20260831
worktree_id: 7360d78d97884e9f
task_id: coverage-local-uv-resolver
actor:
  runtime: grok
  agent: grok-4.6
  model: null
created_at: '2026-08-31T13:56:50.660813+00:00'
source_refs:
- scripts/ai/mcp/support/uv_resolver.ps1
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: a70499986ad0c6e705f1aa2993e39663f7d23a7793054eedc5084083fa156179
id: coverage-local-uv-resolver
title: Fix coverage-local MCP uv resolver PATH failures
ttl_days: 14
confidence: episodic
summary: 'Fixed Windows PowerShell uvx PATH enumeration: unary-comma wrap plus @(Get-BioetlPathEntries)
  nested the whole PATH; Path.Combine joined entries with spaces so Test-Path stubs
  matched a fake concatenated candidate instead of Python313/Scripts and .local/bin.'
---

# Episodic summary

## Task

- Title: Fix coverage-local MCP uv resolver PATH failures

## Outcome

- Fixed Windows PowerShell uvx PATH enumeration: unary-comma wrap plus @(Get-BioetlPathEntries) nested the whole PATH; Path.Combine joined entries with spaces so Test-Path stubs matched a fake concatenated candidate instead of Python313/Scripts and .local/bin.

## Lessons learned

- Replace with durable follow-up if needed
