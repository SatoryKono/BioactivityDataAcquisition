---
id: vcr-chembl-limit-mismatch-20260518
title: Resolve ChEMBL VCR limit mismatch in advanced E2E
task_id: vcr-chembl-limit-mismatch-20260518
created_at: '2026-05-18T18:44:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Aligned advanced ChEMBL E2E seed helper with cassette-compatible limits to
  avoid VCR none-mode mismatches; targeted backfill and vacuum scenarios now skip
  cleanly instead of failing on CannotOverwriteExistingCassetteException.
---

# Episodic summary

## Task

- Title: Resolve ChEMBL VCR limit mismatch in advanced E2E

## Outcome

- Aligned advanced ChEMBL E2E seed helper with cassette-compatible limits to avoid VCR none-mode mismatches; targeted backfill and vacuum scenarios now skip cleanly instead of failing on CannotOverwriteExistingCassetteException.

## Lessons learned

- Replace with durable follow-up if needed
