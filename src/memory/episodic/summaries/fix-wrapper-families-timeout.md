---
id: fix-wrapper-families-timeout
title: Fix wrapper families timeout from composition lazy export deep import chain
task_id: fix_wrapper_families_timeout
created_at: '2026-06-15T15:23:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Preserved canonical registry_api -> factories.pipeline.registry register_all_pipelines
  identity while making factories.pipeline.registry lighter at import time by removing
  the runtime GenericPipelineFactory import. This avoids the previous deep import
  chain during unittest.mock.patch in CLI wrapper tests. Refreshed module coverage
  inventory and architecture quality scorecard hashes; verified wrapper families,
  canonical module paths, registry consistency, and architecture scorecard tests on
  Linux and Windows.
---

# Episodic summary

## Task

- Title: Fix wrapper families timeout from composition lazy export deep import chain

## Outcome

- Preserved canonical registry_api -> factories.pipeline.registry register_all_pipelines identity while making factories.pipeline.registry lighter at import time by removing the runtime GenericPipelineFactory import. This avoids the previous deep import chain during unittest.mock.patch in CLI wrapper tests. Refreshed module coverage inventory and architecture quality scorecard hashes; verified wrapper families, canonical module paths, registry consistency, and architecture scorecard tests on Linux and Windows.

## Lessons learned

- Replace with durable follow-up if needed
