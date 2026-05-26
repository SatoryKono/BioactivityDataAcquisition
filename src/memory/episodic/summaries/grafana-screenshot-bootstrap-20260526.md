---
id: grafana-screenshot-bootstrap-20260526
title: grafana screenshot bootstrap script
task_id: grafana-screenshot-bootstrap-20260526
created_at: '2026-05-26T04:05:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh
  to bootstrap repo-local Grafana screenshot runtime by checking Chromium shared libs,
  optionally attempting apt install, installing npm deps, downloading Playwright Chromium,
  and running launch/screenshot smoke. Updated grafana/README.md to point operators
  to the new bootstrap script. Validated with bash -n, --help, and confirmed expected
  fail-fast apt hint on hosts missing libnspr4/libnss3/libasound2.
---

# Episodic summary

## Task

- Title: grafana screenshot bootstrap script

## Outcome

- Added scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh to bootstrap repo-local Grafana screenshot runtime by checking Chromium shared libs, optionally attempting apt install, installing npm deps, downloading Playwright Chromium, and running launch/screenshot smoke. Updated grafana/README.md to point operators to the new bootstrap script. Validated with bash -n, --help, and confirmed expected fail-fast apt hint on hosts missing libnspr4/libnss3/libasound2.

## Lessons learned

- Replace with durable follow-up if needed
