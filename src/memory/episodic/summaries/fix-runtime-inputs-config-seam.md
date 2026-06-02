---
id: fix-runtime-inputs-config-seam
title: Fix runtime inputs resolver config_access seam regression
task_id: fix-runtime-inputs-config-seam
created_at: '2026-06-02T08:44:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/inputs_resolver.py
summary: Updated inputs_resolver.py to import and default load_source_config through
  the runtime config_access seam, then refreshed module coverage inventory and revalidated
  the seam guard plus coverage hash guard.
---

# Episodic summary

## Task

- Title: Fix runtime inputs resolver config_access seam regression

## Outcome

- Updated inputs_resolver.py to import and default load_source_config through the runtime config_access seam, then refreshed module coverage inventory and revalidated the seam guard plus coverage hash guard.

## Lessons learned

- Replace with durable follow-up if needed
