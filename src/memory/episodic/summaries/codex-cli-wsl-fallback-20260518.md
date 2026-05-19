---
id: codex-cli-wsl-fallback-20260518
title: Fix Codex launcher WSL fallback
task_id: codex-cli-wsl-fallback-20260518
created_at: '2026-05-18T18:11:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ops/launchers/codex/codex.bat
summary: Updated Windows Codex batch launchers to resolve wsl.exe via %WINDIR%\System32
  fallback when PATH does not expose wsl, preserving explicit distro support and manual
  path conversion.
---

# Episodic summary

## Task

- Title: Fix Codex launcher WSL fallback

## Outcome

- Updated Windows Codex batch launchers to resolve wsl.exe via %WINDIR%\System32 fallback when PATH does not expose wsl, preserving explicit distro support and manual path conversion.

## Lessons learned

- Replace with durable follow-up if needed
