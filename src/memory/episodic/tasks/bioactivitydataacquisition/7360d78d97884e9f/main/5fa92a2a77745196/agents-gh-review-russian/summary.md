---
record_id: agents-gh-review-russian
record_type: working
repo_id: bioactivitydataacquisition
git_commit: cea042aa5b4d7753ea724ee6e14dfd69d85f3054
branch: main
worktree_id: 7360d78d97884e9f
task_id: agents-gh-review-russian
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-09-02T04:59:52.594730+00:00'
source_refs:
- AGENTS.md
- tests/architecture/test_gitignore_secret_and_agents_policy.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 27a10d021323292094c0bfdcfbb8b3be278172858dd8cc0519b558fb96d5a4b2
id: agents-gh-review-russian
title: Set Russian language for agent gh reviews
ttl_days: 14
confidence: episodic
summary: Required Russian text for GitHub PR review bodies and inline comments across
  Codex, Junie, Devin, Copilot, Gemini, Cursor, and Windsurf entrypoints; added a
  cross-surface architecture contract test. Junie parity, Codex doctor, Ruff, 11 targeted
  tests, docs drift, links, and cleanup inventory passed. Machine-local Windsurf workflow
  deploy remains absent and was not created.
---

# Episodic summary

## Task

- Title: Set Russian language for agent gh reviews

## Outcome

- Required Russian text for GitHub PR review bodies and inline comments across Codex, Junie, Devin, Copilot, Gemini, Cursor, and Windsurf entrypoints; added a cross-surface architecture contract test. Junie parity, Codex doctor, Ruff, 11 targeted tests, docs drift, links, and cleanup inventory passed. Machine-local Windsurf workflow deploy remains absent and was not created.

## Lessons learned

- Replace with durable follow-up if needed
