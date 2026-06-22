---
id: rf014-cli-config-helper-import-fix
title: Fix RF-014 cli config helper-owner import ratchet
task_id: rf014-cli-config-helper-import-fix
created_at: '2026-06-22T17:42:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_rf014_composition_bootstrap_closeout.py
summary: Restored the explicit RF-014 helper-owner import from pipeline_config_api
  in bootstrap/cli/config.py while preserving the patchable create_pipeline_config_loader
  seam and keeping the surface under the ratchet line limit.
---

# Episodic summary

## Task

- Title: Fix RF-014 cli config helper-owner import ratchet

## Outcome

- Restored the explicit RF-014 helper-owner import from pipeline_config_api in bootstrap/cli/config.py while preserving the patchable create_pipeline_config_loader seam and keeping the surface under the ratchet line limit.

## Lessons learned

- Replace with durable follow-up if needed
