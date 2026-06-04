---
id: fix-services-factory-dq-import-timeout-20260604
title: Fix services factory DQ import timeout
task_id: fix-services-factory-dq-import-timeout-20260604
created_at: '2026-06-04T12:20:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- PyCharm pytest timeout stack 2026-06-04
summary: Reduced services.factory import-time fanout by lazy-loading DQ analyzers/report
  writer, storage factory, ServicesBuilder, service package creation-support exports,
  callback PipelineContext types, and quarantine/checkpoint/lock adapters. Preserved
  patchable StorageFactory.create seam with a lightweight proxy. Verified services.factory
  patch target resolves without loading pyarrow, DQ package, or storage package; targeted
  factory/DQ/smoke tests and module coverage hash guard passed. One unrelated storage
  CSV exporter test still fails.
---

# Episodic summary

## Task

- Title: Fix services factory DQ import timeout

## Outcome

- Reduced services.factory import-time fanout by lazy-loading DQ analyzers/report writer, storage factory, ServicesBuilder, service package creation-support exports, callback PipelineContext types, and quarantine/checkpoint/lock adapters. Preserved patchable StorageFactory.create seam with a lightweight proxy. Verified services.factory patch target resolves without loading pyarrow, DQ package, or storage package; targeted factory/DQ/smoke tests and module coverage hash guard passed. One unrelated storage CSV exporter test still fails.

## Lessons learned

- Replace with durable follow-up if needed
