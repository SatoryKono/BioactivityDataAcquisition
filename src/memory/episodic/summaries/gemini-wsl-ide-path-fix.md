---
id: gemini-wsl-ide-path-fix
title: Fix Gemini WSL launch with Windows IDE workspace path
task_id: gemini-wsl-ide-path-fix
created_at: '2026-05-27T06:10:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ai/gemini/helper/wsl-support.ps1
summary: Updated Gemini PowerShell WSL helper to unset GEMINI_CLI_IDE_WORKSPACE_PATH
  before entering Linux, preventing Windows drive paths such as E:\ from being split
  by Gemini CLI as a Linux path delimiter.
---

# Episodic summary

## Task

- Title: Fix Gemini WSL launch with Windows IDE workspace path

## Outcome

- Updated Gemini PowerShell WSL helper to unset GEMINI_CLI_IDE_WORKSPACE_PATH before entering Linux, preventing Windows drive paths such as E:\ from being split by Gemini CLI as a Linux path delimiter.

## Lessons learned

- Replace with durable follow-up if needed
