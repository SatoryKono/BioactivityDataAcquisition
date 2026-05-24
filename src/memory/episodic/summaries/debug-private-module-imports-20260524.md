---
id: debug-private-module-imports-20260524
title: Fix private-module import violations
task_id: debug-private-module-imports-20260524
created_at: '2026-05-24T13:23:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/core/preflight/service.py
summary: Replaced cross-owner imports of infrastructure.config._base with settings_api
  and localized preflight health emission to preflight.service to satisfy owner-aware
  private-module import guardrails.
---

# Episodic summary

## Task

- Title: Fix private-module import violations

## Outcome

- Replaced cross-owner imports of infrastructure.config._base with settings_api and localized preflight health emission to preflight.service to satisfy owner-aware private-module import guardrails.

## Lessons learned

- Replace with durable follow-up if needed
