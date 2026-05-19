---
id: architecture-regressions-fix-wave
title: Fix architecture and governance regression wave
task_id: architecture-regressions-fix-wave
created_at: '2026-05-19T08:22:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/checkpoint_service.py
summary: Retired the stale domains.run.command wrapper, refactored checkpoint and
  observability services under architecture size/complexity guards, restored SilverWriter
  root validation seam names, and refreshed dependency/VCR/observability/filter/governance
  baselines and registries.
---

# Episodic summary

## Task

- Title: Fix architecture and governance regression wave

## Outcome

- Retired the stale domains.run.command wrapper, refactored checkpoint and observability services under architecture size/complexity guards, restored SilverWriter root validation seam names, and refreshed dependency/VCR/observability/filter/governance baselines and registries.

## Lessons learned

- Replace with durable follow-up if needed
