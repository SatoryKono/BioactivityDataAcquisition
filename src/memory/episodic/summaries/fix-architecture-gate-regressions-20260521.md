---
id: fix-architecture-gate-regressions-20260521
title: Fix scripts catalog and RF014 architecture gate regressions
task_id: fix-architecture-gate-regressions-20260521
created_at: '2026-05-21T14:07:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_scripts_catalog_governance.py
- tests/architecture/test_rf014_composition_bootstrap_closeout.py
- tests/architecture/test_compatibility_facade_inventory.py
summary: Fixed scripts catalog governance by teaching inventory discovery to count
  unified dispatcher command module mappings, refreshed the scripts inventory manifest,
  removed stale lifecycle entries for Docker setup helpers that are now active, kept
  RF-014 CLI config seam at 64 lines by moving DQ pipeline YAML coercion into a helper,
  and removed the unused composition _metrics_publication compatibility wrapper so
  compatibility facade docstring scanning is clean.
---

# Episodic summary

## Task

- Title: Fix scripts catalog and RF014 architecture gate regressions

## Outcome

- Fixed scripts catalog governance by teaching inventory discovery to count unified dispatcher command module mappings, refreshed the scripts inventory manifest, removed stale lifecycle entries for Docker setup helpers that are now active, kept RF-014 CLI config seam at 64 lines by moving DQ pipeline YAML coercion into a helper, and removed the unused composition _metrics_publication compatibility wrapper so compatibility facade docstring scanning is clean.

## Lessons learned

- Replace with durable follow-up if needed
