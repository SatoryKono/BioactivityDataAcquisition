---
id: issue-4036-cli-validate-pipeline-name-export-removal
title: Issue 4036 CLI validate_pipeline_name export removal
task_id: issue-4036-cli-validate-pipeline-name-export-removal
created_at: '2026-05-13T17:52:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Removed validate_pipeline_name from bioetl.interfaces.cli package-root, moved
  remaining tests to domains.run.support, added package-root absence guard, and validated
  with py_compile plus targeted CLI pytest slice.
---

# Episodic summary

## Task

- Title: Issue 4036 CLI validate_pipeline_name export removal

## Outcome

- Removed validate_pipeline_name from bioetl.interfaces.cli package-root, moved remaining tests to domains.run.support, added package-root absence guard, and validated with py_compile plus targeted CLI pytest slice.

## Lessons learned

- Replace with durable follow-up if needed
