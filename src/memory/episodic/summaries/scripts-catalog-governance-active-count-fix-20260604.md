---
id: scripts-catalog-governance-active-count-fix-20260604
title: Fix scripts catalog active count drift
task_id: scripts-catalog-governance-active-count-fix-20260604
created_at: '2026-06-04T11:43:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/scripts_lifecycle_registry.json
- configs/quality/scripts_inventory_manifest.json
summary: Lowered scripts active surface back to cap by classifying src/tools/apply_elk_layout.py
  and src/tools/differentiate_linkstyle.py as supporting legacy_manual_utility entries
  in scripts lifecycle registry and regenerating scripts inventory manifest.
---

# Episodic summary

## Task

- Title: Fix scripts catalog active count drift

## Outcome

- Lowered scripts active surface back to cap by classifying src/tools/apply_elk_layout.py and src/tools/differentiate_linkstyle.py as supporting legacy_manual_utility entries in scripts lifecycle registry and regenerating scripts inventory manifest.

## Lessons learned

- Replace with durable follow-up if needed
