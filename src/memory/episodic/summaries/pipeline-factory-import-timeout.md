---
id: pipeline-factory-import-timeout
title: Fix pipeline factory import timeout on Windows
task_id: pipeline-factory-import-timeout
created_at: '2026-06-16T08:22:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/factories/services/pipeline_batch_executor_builder.py
summary: Deferred Gold lifecycle metric import in the pipeline batch executor builder
  so pipeline factory registry tests no longer trigger heavy observability metric
  imports at module load time, and updated the skip_gold metric seam test accordingly.
---

# Episodic summary

## Task

- Title: Fix pipeline factory import timeout on Windows

## Outcome

- Deferred Gold lifecycle metric import in the pipeline batch executor builder so pipeline factory registry tests no longer trigger heavy observability metric imports at module load time, and updated the skip_gold metric seam test accordingly.

## Lessons learned

- Replace with durable follow-up if needed
