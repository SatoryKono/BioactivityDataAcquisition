---
id: grafana-screenshot-bootstrap-win-pythonfix-20260526
title: windows screenshot bootstrap python fallback
task_id: grafana-screenshot-bootstrap-win-pythonfix-20260526
created_at: '2026-05-26T04:18:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated setup_grafana_screenshot_runtime.ps1 to remove the hard dependency
  on a global uv binary. The script now resolves an active python command first and
  falls back to .venv-win\Scripts\python.exe from the repository for rerender-grafana
  smoke and operator follow-up commands. Updated grafana/README.md to document that
  a global uv install is no longer required on Windows. Validation was source-level
  only because pwsh is not available on the current Linux host.
---

# Episodic summary

## Task

- Title: windows screenshot bootstrap python fallback

## Outcome

- Updated setup_grafana_screenshot_runtime.ps1 to remove the hard dependency on a global uv binary. The script now resolves an active python command first and falls back to .venv-win\Scripts\python.exe from the repository for rerender-grafana smoke and operator follow-up commands. Updated grafana/README.md to document that a global uv install is no longer required on Windows. Validation was source-level only because pwsh is not available on the current Linux host.

## Lessons learned

- Replace with durable follow-up if needed
