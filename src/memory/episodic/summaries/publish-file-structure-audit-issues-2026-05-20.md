---
id: publish-file-structure-audit-issues-2026-05-20
title: Publish GitHub issues from file structure audit
task_id: publish-file-structure-audit-issues-2026-05-20
created_at: '2026-05-20T04:34:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Reviewed the 2026-05-19 file-structure cleanup audit against current repo
  state. Root-hygiene findings RH-014/RH-015/RH-016 were already published and later
  closed; root audit now passes, .env is untracked, .codex/tmp is ignored, and prior
  unknown paths are absent. Published one new residual issue #4352 for live AI runtime
  local-env governance drift: scripts/ai/vibe/.env.vibe lacks explicit ignore coverage
  and repo-maintained hygiene/setup surfaces still contain obsolete env path references.'
---

# Episodic summary

## Task

- Title: Publish GitHub issues from file structure audit

## Outcome

- Reviewed the 2026-05-19 file-structure cleanup audit against current repo state. Root-hygiene findings RH-014/RH-015/RH-016 were already published and later closed; root audit now passes, .env is untracked, .codex/tmp is ignored, and prior unknown paths are absent. Published one new residual issue #4352 for live AI runtime local-env governance drift: scripts/ai/vibe/.env.vibe lacks explicit ignore coverage and repo-maintained hygiene/setup surfaces still contain obsolete env path references.

## Lessons learned

- Replace with durable follow-up if needed
