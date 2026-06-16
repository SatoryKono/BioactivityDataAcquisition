---
id: fix-grafana-rerender-timeout
title: Fix Grafana rerender timeout fallback
task_id: fix_grafana_rerender_timeout
created_at: '2026-06-15T17:58:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Prevented rerender_grafana_screenshots auto-fallback from probing Grafana
  frontend settings after render failures, which could block on live HTTP reads in
  unit tests and local failure paths. Added a regression test that asserts auto fallback
  skips the frontend probe while preserving detailed render hints for non-auto modes.
---

# Episodic summary

## Task

- Title: Fix Grafana rerender timeout fallback

## Outcome

- Prevented rerender_grafana_screenshots auto-fallback from probing Grafana frontend settings after render failures, which could block on live HTTP reads in unit tests and local failure paths. Added a regression test that asserts auto fallback skips the frontend probe while preserving detailed render hints for non-auto modes.

## Lessons learned

- Replace with durable follow-up if needed
