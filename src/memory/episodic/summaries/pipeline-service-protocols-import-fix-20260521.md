---
id: pipeline-service-protocols-import-fix-20260521
title: Restore missing pipeline_service_protocols import path
task_id: pipeline-service-protocols-import-fix-20260521
created_at: '2026-05-21T10:37:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added src/bioetl/application/core/pipeline_service_protocols.py as the owner
  module for PipelineStorageProtocol and PipelineServicesProtocol so application-core
  imports no longer fail on a missing module path. Verified direct src import and
  py_compile; the long semantic-audit pytest module still needs a full rerun outside
  the bounded sandbox timeout if you want end-to-end confirmation.
---

# Episodic summary

## Task

- Title: Restore missing pipeline_service_protocols import path

## Outcome

- Added src/bioetl/application/core/pipeline_service_protocols.py as the owner module for PipelineStorageProtocol and PipelineServicesProtocol so application-core imports no longer fail on a missing module path. Verified direct src import and py_compile; the long semantic-audit pytest module still needs a full rerun outside the bounded sandbox timeout if you want end-to-end confirmation.

## Lessons learned

- Replace with durable follow-up if needed
