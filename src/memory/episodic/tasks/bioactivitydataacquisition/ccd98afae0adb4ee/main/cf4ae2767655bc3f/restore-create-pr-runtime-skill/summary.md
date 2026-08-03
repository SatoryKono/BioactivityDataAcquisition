---
record_id: restore-create-pr-runtime-skill
record_type: working
repo_id: bioactivitydataacquisition
git_commit: ebfd8a829e74815631cea083f779e93f5cb2693c
branch: main
worktree_id: ccd98afae0adb4ee
task_id: restore-create-pr-runtime-skill
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T07:10:04.103534+00:00'
source_refs:
- .codex/skills/create-pr/SKILL.md
- .junie/skills/create-pr/SKILL.md
- .devin/skills/create-pr/SKILL.md
- docs/00-project/ai/skills/local/create-pr/SKILL.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 029a380b50cf848ec251676ccd3872f00f5da95a449cdbcaa41c4c92d8b92f0f
id: restore-create-pr-runtime-skill
title: Restore create-pr runtime skill
ttl_days: 14
confidence: episodic
summary: Restored the active create-pr skill entrypoint and OpenAI metadata across
  Codex, Junie, Devin, and docs mirrors, and restored only its catalog membership.
  AI governance links, Codex-Junie parity, Codex-Devin/docs skill mirror checks, and
  documentation drift checks all pass.
---

# Episodic summary

## Task

- Title: Restore create-pr runtime skill

## Outcome

- Restored the active create-pr skill entrypoint and OpenAI metadata across Codex, Junie, Devin, and docs mirrors, and restored only its catalog membership. AI governance links, Codex-Junie parity, Codex-Devin/docs skill mirror checks, and documentation drift checks all pass.

## Lessons learned

- Replace with durable follow-up if needed
