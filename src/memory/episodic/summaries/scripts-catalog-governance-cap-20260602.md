---
id: scripts-catalog-governance-cap-20260602
title: Fix scripts catalog governance cap drift
task_id: scripts-catalog-governance-cap-20260602
created_at: '2026-06-02T09:20:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Updated scripts catalog lifecycle.active_script_count_max from 368 to 372
  in scripts/engineering/repo/catalog.yaml to match the committed scripts inventory
  manifest active count and restore the fail-fast reviewed baseline. Verified test_scripts_catalog_governance
  plus adjacent scripts inventory/lifecycle guard tests are green after the synchronization.
---

# Episodic summary

## Task

- Title: Fix scripts catalog governance cap drift

## Outcome

- Updated scripts catalog lifecycle.active_script_count_max from 368 to 372 in scripts/engineering/repo/catalog.yaml to match the committed scripts inventory manifest active count and restore the fail-fast reviewed baseline. Verified test_scripts_catalog_governance plus adjacent scripts inventory/lifecycle guard tests are green after the synchronization.

## Lessons learned

- Replace with durable follow-up if needed
