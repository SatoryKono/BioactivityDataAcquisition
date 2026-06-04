---
id: fix-gold-import-timeout-after-5055-20260604
title: Fix GoldWriter import timeout after TYPE_CHECKING cleanup
task_id: fix-gold-import-timeout-after-5055-20260604
created_at: '2026-06-04T11:24:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Reduced GoldWriter and service bundle import-time cost by keeping heavy pyarrow,
  pandera, prometheus, metadata, DQ evaluator, and normalization imports out of cold
  facade imports; verified gold_writer import remains fast without heavy libs, services.bundle
  import completes under bounded timeout, regenerated dependency map artifacts, refreshed
  module coverage source hash in source-only mode because reports/coverage/coverage.xml
  is absent, and ran targeted unit/architecture/smoke checks.
---

# Episodic summary

## Task

- Title: Fix GoldWriter import timeout after TYPE_CHECKING cleanup

## Outcome

- Reduced GoldWriter and service bundle import-time cost by keeping heavy pyarrow, pandera, prometheus, metadata, DQ evaluator, and normalization imports out of cold facade imports; verified gold_writer import remains fast without heavy libs, services.bundle import completes under bounded timeout, regenerated dependency map artifacts, refreshed module coverage source hash in source-only mode because reports/coverage/coverage.xml is absent, and ran targeted unit/architecture/smoke checks.

## Lessons learned

- Replace with durable follow-up if needed
