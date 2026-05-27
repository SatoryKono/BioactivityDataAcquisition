---
id: grafana-screenshot-bootstrap-win-nodefix-20260526
title: windows screenshot bootstrap node fallback
task_id: grafana-screenshot-bootstrap-win-nodefix-20260526
created_at: '2026-05-26T04:15:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated setup_grafana_screenshot_runtime.ps1 to self-bootstrap a portable
  official Node.js LTS toolchain on Windows when node/npm are missing from PATH. The
  script now resolves the latest Windows x64 LTS release from nodejs.org/dist/index.json,
  downloads and extracts it under %LOCALAPPDATA%\bioetl-tools\nodejs, prepends it
  to PATH for the current process, and continues with npm install, Playwright Chromium
  download, and optional rerender smoke. Updated grafana/README.md to document that
  a global Node installation is no longer required on Windows. Validation remained
  source-level only because pwsh is not installed on the current Linux host.
---

# Episodic summary

## Task

- Title: windows screenshot bootstrap node fallback

## Outcome

- Updated setup_grafana_screenshot_runtime.ps1 to self-bootstrap a portable official Node.js LTS toolchain on Windows when node/npm are missing from PATH. The script now resolves the latest Windows x64 LTS release from nodejs.org/dist/index.json, downloads and extracts it under %LOCALAPPDATA%\bioetl-tools\nodejs, prepends it to PATH for the current process, and continues with npm install, Playwright Chromium download, and optional rerender smoke. Updated grafana/README.md to document that a global Node installation is no longer required on Windows. Validation remained source-level only because pwsh is not installed on the current Linux host.

## Lessons learned

- Replace with durable follow-up if needed
