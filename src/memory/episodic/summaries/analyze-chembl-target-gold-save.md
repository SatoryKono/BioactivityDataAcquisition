---
id: analyze-chembl-target-gold-save
title: Analyze why chembl_target pipeline does not save Gold layer
task_id: analyze-chembl-target-gold-save
created_at: '2026-06-01T05:38:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/target.yaml
summary: 'Read-only analysis of chembl_target Gold persistence: Gold is enabled in
  config, write path persists non-empty gold_records, historical run ledger shows
  gold:chembl.target publication with 994 records, but current local filesystem lacks
  data/output/gold/chembl/target and current target silver table files. Likely control-plane/filesystem
  artifact divergence rather than Gold disabled in pipeline.'
---

# Episodic summary

## Task

- Title: Analyze why chembl_target pipeline does not save Gold layer

## Outcome

- Read-only analysis of chembl_target Gold persistence: Gold is enabled in config, write path persists non-empty gold_records, historical run ledger shows gold:chembl.target publication with 994 records, but current local filesystem lacks data/output/gold/chembl/target and current target silver table files. Likely control-plane/filesystem artifact divergence rather than Gold disabled in pipeline.

## Lessons learned

- Replace with durable follow-up if needed
