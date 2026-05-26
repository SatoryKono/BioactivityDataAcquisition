---
id: grafana-screenshot-bootstrap-win-20260526
title: windows grafana screenshot bootstrap
task_id: grafana-screenshot-bootstrap-win-20260526
created_at: '2026-05-26T04:11:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1
  so Windows PowerShell users can bootstrap Grafana screenshot capture without bash.
  The script installs repo-local npm deps, downloads Playwright Chromium, runs a headless
  browser launch smoke, and optionally runs rerender-grafana smoke. Updated grafana/README.md
  with the PowerShell invocation. Validation on this Linux host was limited to source
  review because pwsh is not installed here.
---

# Episodic summary

## Task

- Title: windows grafana screenshot bootstrap

## Outcome

- Added scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1 so Windows PowerShell users can bootstrap Grafana screenshot capture without bash. The script installs repo-local npm deps, downloads Playwright Chromium, runs a headless browser launch smoke, and optionally runs rerender-grafana smoke. Updated grafana/README.md with the PowerShell invocation. Validation on this Linux host was limited to source review because pwsh is not installed here.

## Lessons learned

- Replace with durable follow-up if needed
