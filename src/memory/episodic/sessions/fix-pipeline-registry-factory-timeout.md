---
id: fix-pipeline-registry-factory-timeout
title: Fix pipeline registry factory timeout in pipeline factory tests
task_id: fix_pipeline_registry_factory_timeout
created_at: '2026-06-15T17:22:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Active task session context.
query: tests/unit/interfaces/factories/test_pipeline_factories.py timeout caused by
  pipeline.registry __getattr__ constructing heavy factory/provider chain
---

# Session note

## Task

- Title: Fix pipeline registry factory timeout in pipeline factory tests
- Retrieval query: tests/unit/interfaces/factories/test_pipeline_factories.py timeout caused by pipeline.registry __getattr__ constructing heavy factory/provider chain

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
