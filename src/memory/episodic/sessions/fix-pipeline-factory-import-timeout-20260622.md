---
id: fix-pipeline-factory-import-timeout-20260622
title: Fix pipeline factory import timeout
task_id: fix-pipeline-factory-import-timeout-20260622
created_at: '2026-06-22T16:47:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/factories/test_pipeline_factories.py
summary: Active task session context.
query: test_pipeline_factories registry __getattr__ GenericPipelineFactory import
  timeout _record_processor_policy_support
---

# Session note

## Task

- Title: Fix pipeline factory import timeout
- Retrieval query: test_pipeline_factories registry __getattr__ GenericPipelineFactory import timeout _record_processor_policy_support

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
