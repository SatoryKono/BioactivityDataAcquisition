---
id: fix-grafana-tooling-fetch-json-timeout-20260601
title: Fix Grafana audit tooling timeout fake failures
task_id: fix-grafana-tooling-fetch-json-timeout-20260601
created_at: '2026-06-01T12:47:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated Grafana audit unit-test fakes to accept the production _fetch_json
  keyword-only timeout_seconds parameter and assert it matches config.request_timeout_seconds.
  Targeted failed tests, full Grafana dashboard tooling unit file, and ruff check
  now pass.
---

# Episodic summary

## Task

- Title: Fix Grafana audit tooling timeout fake failures

## Outcome

- Updated Grafana audit unit-test fakes to accept the production _fetch_json keyword-only timeout_seconds parameter and assert it matches config.request_timeout_seconds. Targeted failed tests, full Grafana dashboard tooling unit file, and ruff check now pass.

## Lessons learned

- Replace with durable follow-up if needed
