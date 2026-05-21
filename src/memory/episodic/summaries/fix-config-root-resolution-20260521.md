---
id: fix-config-root-resolution-20260521
title: Fix pipeline config root resolution regression
task_id: fix-config-root-resolution-20260521
created_at: '2026-05-21T08:12:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/pipeline_config_loader.py
- src/bioetl/infrastructure/config/domain_config_resolver.py
- src/bioetl/infrastructure/config/config_root.py
summary: Fixed pipeline config root propagation for explicit relative configs roots
  and validated failing chembl pipeline tests.
---

# Episodic summary

## Task

- Title: Fix pipeline config root resolution regression

## Outcome

- Fixed pipeline config root propagation for explicit relative configs roots and validated failing chembl pipeline tests.

## Lessons learned

- Replace with durable follow-up if needed
