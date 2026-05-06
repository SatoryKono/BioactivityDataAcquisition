---
id: lineage-metadata-protocol-import-error
title: Fix PipelineMetadataProtocol import error
task_id: lineage-metadata-protocol-import-error
created_at: '2026-05-06T08:21:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/lineage/metadata_assembler_support.py
summary: Fixed application test collection ImportError by restoring compatibility
  aliases PipelineMetadataProtocol and RuntimeMetadataProtocol in metadata_assembler_support.py,
  pointing to the renamed PipelineMetadataBuilderProtocol and RuntimeMetadataBuilderProtocol.
  Verified imports, affected application collection, metadata assembler unit tests,
  and ruff.
---

# Episodic summary

## Task

- Title: Fix PipelineMetadataProtocol import error

## Outcome

- Fixed application test collection ImportError by restoring compatibility aliases PipelineMetadataProtocol and RuntimeMetadataProtocol in metadata_assembler_support.py, pointing to the renamed PipelineMetadataBuilderProtocol and RuntimeMetadataBuilderProtocol. Verified imports, affected application collection, metadata assembler unit tests, and ruff.

## Lessons learned

- Replace with durable follow-up if needed
