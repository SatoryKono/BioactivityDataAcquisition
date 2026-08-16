---
record_id: mcp-remediation-8843-8846
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 51a024fc20989aea603b6caf7116b3ca97348cd2
branch: main
worktree_id: b5393af69d37a674
task_id: mcp-remediation-8843-8846
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-08-16T14:02:14.283875+00:00'
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/commit/2b9475bc3a386940cda05956c67b88bd9f00a946
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 88c55432250db15a05fce107a2f9c8de381a2c06c1e652a0c23be547759c74a1
id: mcp-remediation-8843-8846
title: Implement and close MCP remediation issues 8843-8846
ttl_days: 14
confidence: episodic
summary: Implemented exact persisted stable/shared parity across local MCP projections,
  deterministic shared-plane cold start, offline ast-grep preflight, regression coverage,
  and synchronized operator docs. Targeted pytest, Ruff, profile, tracked/local parity,
  doctor, docs, debt, static and live stable checks passed; nine required endpoints
  healthy and Codex lists exactly ten entries. PowerShell-only tests skipped in WSL.
  Proof-or-Stop plan was unavailable because its fixed 20-second git diff timeout
  is shorter than this mounted LFS checkout; governance dry-run separately found 21
  pre-existing expired episodic entries and deleted nothing.
---

# Episodic summary

## Task

- Title: Implement and close MCP remediation issues 8843-8846

## Outcome

- Implemented exact persisted stable/shared parity across local MCP projections, deterministic shared-plane cold start, offline ast-grep preflight, regression coverage, and synchronized operator docs. Targeted pytest, Ruff, profile, tracked/local parity, doctor, docs, debt, static and live stable checks passed; nine required endpoints healthy and Codex lists exactly ten entries. PowerShell-only tests skipped in WSL. Proof-or-Stop plan was unavailable because its fixed 20-second git diff timeout is shorter than this mounted LFS checkout; governance dry-run separately found 21 pre-existing expired episodic entries and deleted nothing.

## Lessons learned

- Replace with durable follow-up if needed
