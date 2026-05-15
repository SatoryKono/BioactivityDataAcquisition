---
id: fix-processed-records-no-data-20260515
title: Fix Processed Records No data
task_id: fix-processed-records-no-data-20260515
created_at: '2026-05-15T07:13:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed live Processed Records No data by restarting bioetl-prometheus after
  lifecycle reload was disabled; verified 17 bioetl_processed_records_* rules loaded
  and panel query returns UNKNOWN/status rows for chembl_publication/backfill.
---

# Episodic summary

## Task

- Title: Fix Processed Records No data

## Outcome

- Fixed live Processed Records No data by restarting bioetl-prometheus after lifecycle reload was disabled; verified 17 bioetl_processed_records_* rules loaded and panel query returns UNKNOWN/status rows for chembl_publication/backfill.

## Lessons learned

- Replace with durable follow-up if needed
