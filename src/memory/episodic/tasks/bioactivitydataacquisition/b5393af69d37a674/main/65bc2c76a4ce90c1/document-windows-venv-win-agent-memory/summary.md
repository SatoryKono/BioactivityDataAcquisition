---
record_id: document-windows-venv-win-agent-memory
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 2069d69eddffbcdce804ef6a20ebf0aade72c454
branch: main
worktree_id: b5393af69d37a674
task_id: document-windows-venv-win-agent-memory
actor:
  runtime: codex
  agent: py-doc-bot
  model: gpt-5.6
created_at: '2026-08-09T10:11:28.368497+00:00'
source_refs:
- docs/00-project/ai/memory/agent-memory.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 97f2a18d6d9736a17a4aafe609dd17affa345a26cc24c82952834083745f4311
id: document-windows-venv-win-agent-memory
title: Document venv-win for Windows agents
ttl_days: 14
confidence: episodic
summary: Added shared agent-memory guidance requiring native Windows and PowerShell
  agents to use the repository-local .venv-win environment, while keeping WSL/Linux
  environments separate. Documentation drift and memory validation passed; the broad
  link check found two unrelated pre-existing broken links in extended-docs-index.md.
---

# Episodic summary

## Task

- Title: Document venv-win for Windows agents

## Outcome

- Added shared agent-memory guidance requiring native Windows and PowerShell agents to use the repository-local .venv-win environment, while keeping WSL/Linux environments separate. Documentation drift and memory validation passed; the broad link check found two unrelated pre-existing broken links in extended-docs-index.md.

## Lessons learned

- Replace with durable follow-up if needed
