---
id: chembl-target-protein-classification-loc-20260601
title: Fix composition file size and private-application-import guards for chembl
  target protein classification provider
task_id: chembl-target-protein-classification-loc-20260601
created_at: '2026-06-01T14:59:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/providers/_chembl_target_protein_classification_data_source.py
summary: Split ChEMBL target protein-classification composition wrapper into wrapper,
  relation builder, helpers, and a composition-local delegation mixin; removed private
  application mixin imports, kept each composition module under the LOC gate, and
  refreshed module coverage inventory after targeted architecture and provider tests
  passed.
---

# Episodic summary

## Task

- Title: Fix composition file size and private-application-import guards for chembl target protein classification provider

## Outcome

- Split ChEMBL target protein-classification composition wrapper into wrapper, relation builder, helpers, and a composition-local delegation mixin; removed private application mixin imports, kept each composition module under the LOC gate, and refreshed module coverage inventory after targeted architecture and provider tests passed.

## Lessons learned

- Replace with durable follow-up if needed
