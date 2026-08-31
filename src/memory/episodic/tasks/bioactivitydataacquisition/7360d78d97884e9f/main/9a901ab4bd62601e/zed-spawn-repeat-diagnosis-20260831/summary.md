---
record_id: zed-spawn-repeat-diagnosis-20260831
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 10ee7dc78554ce9c8f3448e58deb17012a7d33d2
branch: main
worktree_id: 7360d78d97884e9f
task_id: zed-spawn-repeat-diagnosis-20260831
actor:
  runtime: codex
  agent: codex
  model: null
created_at: '2026-08-31T12:23:44.555087+00:00'
source_refs:
- .zed/keymap.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: a8ebaed703713f5a6ec8ce55abfb3cd058faa4f09686559ed7ac9562c96baab8
id: zed-spawn-repeat-diagnosis-20260831
title: Diagnose repeated Zed task spawn exit
ttl_days: 14
confidence: episodic
summary: 'Confirmed Zed SonarQube MCP spawn failure: user settings set docker_path=/usr/bin/docker
  on Windows; actual Docker CLI is C:\Program Files\Docker\Docker\resources\bin\docker.exe.
  Repo task::Spawn shortcut is valid and unshadowed. Existing Grok session also logged
  separate skill read/tool errors.'
---

# Episodic summary

## Task

- Title: Diagnose repeated Zed task spawn exit

## Outcome

- Confirmed Zed SonarQube MCP spawn failure: user settings set docker_path=/usr/bin/docker on Windows; actual Docker CLI is C:\Program Files\Docker\Docker\resources\bin\docker.exe. Repo task::Spawn shortcut is valid and unshadowed. Existing Grok session also logged separate skill read/tool errors.

## Lessons learned

- Replace with durable follow-up if needed
