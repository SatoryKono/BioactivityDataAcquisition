---
id: fix-observability-defects-chembl-activity
title: Fix observability defects for chembl_activity
task_id: fix-observability-defects-chembl-activity
created_at: '2026-05-11T10:45:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- workspace:/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/ccd98afae0adb4ee090bbfed89f354b31936eafe0874d43825bf3cb903f3bd1d
summary: 'Fixed health/quarantine backend startup and dashboard/query semantics defects:
  health/quarantine now starts reliably on 8081 with real readiness probe, metrics
  startup no longer hangs via heavy observability facade, Silver Reject Explorer stats
  backend responds and derives Bronze denominators from run manifests, Runtime Error
  Rate panel handles healthy-zero numerators, Workflow Run Outcomes uses increase()
  instead of max_over_time(counter), and dashboard/tests/container smoke are green.'
---

# Episodic summary

## Task

- Title: Fix observability defects for chembl_activity

## Outcome

- Fixed health/quarantine backend startup and dashboard/query semantics defects: health/quarantine now starts reliably on 8081 with real readiness probe, metrics startup no longer hangs via heavy observability facade, Silver Reject Explorer stats backend responds and derives Bronze denominators from run manifests, Runtime Error Rate panel handles healthy-zero numerators, Workflow Run Outcomes uses increase() instead of max_over_time(counter), and dashboard/tests/container smoke are green.

## Lessons learned

- Replace with durable follow-up if needed
