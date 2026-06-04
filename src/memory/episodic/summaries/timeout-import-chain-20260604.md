---
id: timeout-import-chain-20260604
title: Diagnose import-time timeout in service factory chain
task_id: timeout-import-chain-20260604
created_at: '2026-06-04T09:30:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/services/factory.py
summary: Reduced service-factory import-time timeout risk by converting factory-level
  builder/callback/port-factory re-exports and wiring imports to lazy resolution,
  preserving BaseServicesFactory seams while avoiding eager pipeline-builder and validation
  imports during patch setup; updated module coverage source-tree hash and verified
  targeted factory patch tests.
---

# Episodic summary

## Task

- Title: Diagnose import-time timeout in service factory chain

## Outcome

- Reduced service-factory import-time timeout risk by converting factory-level builder/callback/port-factory re-exports and wiring imports to lazy resolution, preserving BaseServicesFactory seams while avoiding eager pipeline-builder and validation imports during patch setup; updated module coverage source-tree hash and verified targeted factory patch tests.

## Lessons learned

- Replace with durable follow-up if needed
