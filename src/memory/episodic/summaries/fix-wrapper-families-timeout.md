---
id: fix-wrapper-families-timeout
title: Fix wrapper families timeout from composition lazy export deep import chain
task_id: fix_wrapper_families_timeout
created_at: '2026-06-15T14:59:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Retargeted bioetl.composition.registry_api.register_all_pipelines lazy export
  from the heavy factories.pipeline.registry module to the lightweight bootstrap.runtime.pipeline_bootstrap_phases
  wrapper so unittest.mock.patch resolves quickly without importing deep pipeline
  assembly. Refreshed module coverage inventory and architecture quality scorecard
  hashes; verified wrapper family, registry consistency, and architecture scorecard
  tests on Linux plus wrapper family and architecture scorecard on Windows.
---

# Episodic summary

## Task

- Title: Fix wrapper families timeout from composition lazy export deep import chain

## Outcome

- Retargeted bioetl.composition.registry_api.register_all_pipelines lazy export from the heavy factories.pipeline.registry module to the lightweight bootstrap.runtime.pipeline_bootstrap_phases wrapper so unittest.mock.patch resolves quickly without importing deep pipeline assembly. Refreshed module coverage inventory and architecture quality scorecard hashes; verified wrapper family, registry consistency, and architecture scorecard tests on Linux plus wrapper family and architecture scorecard on Windows.

## Lessons learned

- Replace with durable follow-up if needed
