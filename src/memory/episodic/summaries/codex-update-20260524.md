---
id: codex-update-20260524
title: Update Codex surfaces
task_id: codex-update-20260524
created_at: '2026-05-24T12:04:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ai/codex/helper/ensure-codex-cli.sh
summary: Updated the repo-managed Codex CLI to 0.133.0 via a temporary /tmp install
  and rsync overlay; confirmed launcher version. Verified user-level npm global install
  is 0.133.0 in ~/.nvm, while /usr/local/bin/codex remains 0.118.0 because current
  user lacks write permission to /usr/local.
---

# Episodic summary

## Task

- Title: Update Codex surfaces

## Outcome

- Updated the repo-managed Codex CLI to 0.133.0 via a temporary /tmp install and rsync overlay; confirmed launcher version. Verified user-level npm global install is 0.133.0 in ~/.nvm, while /usr/local/bin/codex remains 0.118.0 because current user lacks write permission to /usr/local.

## Lessons learned

- Replace with durable follow-up if needed
