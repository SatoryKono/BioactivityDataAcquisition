---
id: chembl-assay-config-path-20260521
title: Fix Windows config path resolution for workflow run
task_id: chembl-assay-config-path-20260521
created_at: '2026-05-21T07:49:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/config_root.py
summary: Fixed canonical config root resolution from src/ to repository root and added
  regression coverage; verified workflow CLI dry-run now loads chembl_assay config
  successfully.
---

# Episodic summary

## Task

- Title: Fix Windows config path resolution for workflow run

## Outcome

- Fixed canonical config root resolution from src/ to repository root and added regression coverage; verified workflow CLI dry-run now loads chembl_assay config successfully.

## Lessons learned

- Replace with durable follow-up if needed
