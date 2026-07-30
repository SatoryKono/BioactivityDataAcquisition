---
record_id: configure-codex-wsl-20260730
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 94780317c8a3d954ed656f92fde23051856f2da5
branch: main
worktree_id: ccd98afae0adb4ee
task_id: configure-codex-wsl-20260730
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T05:36:16.540701+00:00'
source_refs:
- local-shell-profile
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 27bbdf29171d360e3818390976e30828b7c03f2dd7106805eaea9977cafb660e
id: configure-codex-wsl-20260730
title: Verify and configure Codex for WSL
ttl_days: 14
confidence: episodic
summary: Validated WSL2, managed Codex CLI 0.146.0, ChatGPT login, stable/shared MCP
  config and health. Repaired ~/.bashrc by guarding missing ~/.local/bin/env, removing
  inherited npm-prefix conflict before NVM, deduplicating PATH setup, and retaining
  canonical BioETL Codex launcher. Final WSL diagnostics and MCP checks pass; checkout
  remains on slower /mnt/e 9p by user scope.
---

# Episodic summary

## Task

- Title: Verify and configure Codex for WSL

## Outcome

- Validated WSL2, managed Codex CLI 0.146.0, ChatGPT login, stable/shared MCP config and health. Repaired ~/.bashrc by guarding missing ~/.local/bin/env, removing inherited npm-prefix conflict before NVM, deduplicating PATH setup, and retaining canonical BioETL Codex launcher. Final WSL diagnostics and MCP checks pass; checkout remains on slower /mnt/e 9p by user scope.

## Lessons learned

- Replace with durable follow-up if needed
