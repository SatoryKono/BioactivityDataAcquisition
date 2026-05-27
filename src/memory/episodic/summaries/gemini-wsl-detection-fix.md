---
id: gemini-wsl-detection-fix
title: Fix Gemini WSL detection from Windows PowerShell
task_id: gemini-wsl-detection-fix
created_at: '2026-05-27T05:58:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ai/gemini/helper/wsl-support.ps1
summary: Updated Gemini PowerShell WSL helper to resolve wsl.exe via PATH, System32,
  and Sysnative, avoiding hard failures from Get-Command wsl under ErrorActionPreference
  Stop.
---

# Episodic summary

## Task

- Title: Fix Gemini WSL detection from Windows PowerShell

## Outcome

- Updated Gemini PowerShell WSL helper to resolve wsl.exe via PATH, System32, and Sysnative, avoiding hard failures from Get-Command wsl under ErrorActionPreference Stop.

## Lessons learned

- Replace with durable follow-up if needed
