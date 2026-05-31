---
id: close-dashboard-issues-4840-4845
title: Close dashboard audit issues 4840-4845
task_id: close-dashboard-issues-4840-4845
created_at: '2026-05-31T15:08:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/codex/dashboard-audit-20260531/findings.csv
summary: Closed GitHub issues 4840, 4841, 4842, 4844, 4845 after implementing checkpoint
  identity evidence routing, provider-health PromQL fix, exact-run processed-records
  RunLedger source, and no-data classifications for panels 106/242. Left 4843 open
  with blocker comment because Grafana render API returns 500 and Playwright Chromium
  cannot launch without host libnspr4/libnss shared libraries; sudo install is unavailable.
---

# Episodic summary

## Task

- Title: Close dashboard audit issues 4840-4845

## Outcome

- Closed GitHub issues 4840, 4841, 4842, 4844, 4845 after implementing checkpoint identity evidence routing, provider-health PromQL fix, exact-run processed-records RunLedger source, and no-data classifications for panels 106/242. Left 4843 open with blocker comment because Grafana render API returns 500 and Playwright Chromium cannot launch without host libnspr4/libnss shared libraries; sudo install is unavailable.

## Lessons learned

- Replace with durable follow-up if needed
