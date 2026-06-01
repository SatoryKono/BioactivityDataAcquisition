---
id: chembl-target-protein-classification-loc-20260601
title: Fix composition file size limit for chembl target protein classification provider
task_id: chembl-target-protein-classification-loc-20260601
created_at: '2026-06-01T14:47:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/providers/_chembl_target_protein_classification_data_source.py
summary: Split ChEMBL target protein-classification composition wrapper into public
  wrappers, relation builder, and helper modules; removed stale file-size exemption
  and refreshed module coverage inventory after validating the LOC guard and provider
  tests.
---

# Episodic summary

## Task

- Title: Fix composition file size limit for chembl target protein classification provider

## Outcome

- Split ChEMBL target protein-classification composition wrapper into public wrappers, relation builder, and helper modules; removed stale file-size exemption and refreshed module coverage inventory after validating the LOC guard and provider tests.

## Lessons learned

- Replace with durable follow-up if needed
