---
id: chembl-adapter-config-resilience-fields
title: Fix ChEMBL adapter resilience config constructor drift
task_id: chembl-adapter-config-resilience-fields
created_at: '2026-06-03T07:28:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/resilience.py
summary: Extended domain AdapterConfig with resilience knobs and timeout alias, bound
  ChemblAdapter._adapter_config to the resolved config, propagated YAML rate-limit
  and circuit-breaker values, and validated failing ChEMBL resilience tests plus architecture
  drift guards.
---

# Episodic summary

## Task

- Title: Fix ChEMBL adapter resilience config constructor drift

## Outcome

- Extended domain AdapterConfig with resilience knobs and timeout alias, bound ChemblAdapter._adapter_config to the resolved config, propagated YAML rate-limit and circuit-breaker values, and validated failing ChEMBL resilience tests plus architecture drift guards.

## Lessons learned

- Replace with durable follow-up if needed
