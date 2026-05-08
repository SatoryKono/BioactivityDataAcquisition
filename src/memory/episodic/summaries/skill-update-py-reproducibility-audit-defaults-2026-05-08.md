---
id: skill-update-py-reproducibility-audit-defaults-2026-05-08
title: Update py-reproducibility-audit skill defaults and target resolution
task_id: skill-update-py-reproducibility-audit-defaults-2026-05-08
created_at: '2026-05-08T17:48:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated py-reproducibility-audit skill to support explicit target resolution
  for any pipeline or workflow. Added default inputs target_type=pipeline, target_name=chembl_assay,
  execution_mode=fresh_run, run_count=2, limit=1000. Documented fresh_run vs existing_run_ids
  lanes and workflow vs pipeline reporting rules. Synced agents/openai.yaml default
  prompt with the new defaults.
---

# Episodic summary

## Task

- Title: Update py-reproducibility-audit skill defaults and target resolution

## Outcome

- Updated py-reproducibility-audit skill to support explicit target resolution for any pipeline or workflow. Added default inputs target_type=pipeline, target_name=chembl_assay, execution_mode=fresh_run, run_count=2, limit=1000. Documented fresh_run vs existing_run_ids lanes and workflow vs pipeline reporting rules. Synced agents/openai.yaml default prompt with the new defaults.

## Lessons learned

- Replace with durable follow-up if needed
