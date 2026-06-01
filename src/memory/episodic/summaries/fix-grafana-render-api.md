---
id: fix-grafana-render-api
title: Fix Grafana Render API HTTP 500
task_id: fix-grafana-render-api
created_at: '2026-06-01T13:49:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- docker-compose.monitoring.yml
summary: Updated monitoring compose to use pinned Grafana Image Renderer 5.0.0, explicit
  GF_RENDERING_RENDERER_TOKEN/AUTH_TOKEN matching, BROWSER_FLAGS instead of legacy
  RENDERING_ARGS, renderer shm/GOMEMLIMIT, Prometheus renderer scrape, tooling hints,
  tests, and docs. Current live render still times out until the running external
  Grafana/renderer stack is recreated from the updated compose.
---

# Episodic summary

## Task

- Title: Fix Grafana Render API HTTP 500

## Outcome

- Updated monitoring compose to use pinned Grafana Image Renderer 5.0.0, explicit GF_RENDERING_RENDERER_TOKEN/AUTH_TOKEN matching, BROWSER_FLAGS instead of legacy RENDERING_ARGS, renderer shm/GOMEMLIMIT, Prometheus renderer scrape, tooling hints, tests, and docs. Current live render still times out until the running external Grafana/renderer stack is recreated from the updated compose.

## Lessons learned

- Replace with durable follow-up if needed
