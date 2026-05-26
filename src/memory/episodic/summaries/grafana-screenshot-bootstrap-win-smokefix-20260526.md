---
id: grafana-screenshot-bootstrap-win-smokefix-20260526
title: windows screenshot bootstrap smoke fixes
task_id: grafana-screenshot-bootstrap-win-smokefix-20260526
created_at: '2026-05-26T04:27:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Updated setup_grafana_screenshot_runtime.ps1 to fix two real Windows smoke
  defects: Node launch smoke now passes a here-string JS program to node -e so require(''playwright'')
  survives PowerShell argument handling, and Invoke-Step now fails fast on non-zero
  native exit codes instead of continuing after broken smoke commands. Also added
  default local Grafana smoke credentials/admin-changeme and base URL propagation
  into rerender-grafana smoke. Updated grafana/README.md to document the default local
  credential behavior. Validation remained source-level because pwsh is unavailable
  on the current Linux host.'
---

# Episodic summary

## Task

- Title: windows screenshot bootstrap smoke fixes

## Outcome

- Updated setup_grafana_screenshot_runtime.ps1 to fix two real Windows smoke defects: Node launch smoke now passes a here-string JS program to node -e so require('playwright') survives PowerShell argument handling, and Invoke-Step now fails fast on non-zero native exit codes instead of continuing after broken smoke commands. Also added default local Grafana smoke credentials/admin-changeme and base URL propagation into rerender-grafana smoke. Updated grafana/README.md to document the default local credential behavior. Validation remained source-level because pwsh is unavailable on the current Linux host.

## Lessons learned

- Replace with durable follow-up if needed
