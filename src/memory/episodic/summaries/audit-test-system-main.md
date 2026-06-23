---
id: audit-test-system-main
title: Audit BioETL test system on main
task_id: audit-test-system-main
created_at: '2026-06-23T06:34:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests
summary: 'Audited clean main snapshot 8a550695 test system. Key facts: 1834 governed
  test files / 21015 test functions in test-governance report; module coverage inventory
  has 2181 source modules with 0 uncovered/unmeasured and 104 below 85%; domain aggregate
  invariant registry covers Batch, PipelineRun, QuarantineEntry 3/3; Gold contract
  matrix covers 27/27 with golden evidence; Bronze fixture gaps empty; VCR catalog
  has 198 cassettes and 0 duplicate/orphan/metadata-review items; main risks are unit
  lane I/O dilution, repo-wide architecture scan cost, stale slow-test telemetry,
  weak assertion density in transformer/extractor tests, and 26 compatibility test
  files / 12 retained public entrypoints.'
---

# Episodic summary

## Task

- Title: Audit BioETL test system on main

## Outcome

- Audited clean main snapshot 8a550695 test system. Key facts: 1834 governed test files / 21015 test functions in test-governance report; module coverage inventory has 2181 source modules with 0 uncovered/unmeasured and 104 below 85%; domain aggregate invariant registry covers Batch, PipelineRun, QuarantineEntry 3/3; Gold contract matrix covers 27/27 with golden evidence; Bronze fixture gaps empty; VCR catalog has 198 cassettes and 0 duplicate/orphan/metadata-review items; main risks are unit lane I/O dilution, repo-wide architecture scan cost, stale slow-test telemetry, weak assertion density in transformer/extractor tests, and 26 compatibility test files / 12 retained public entrypoints.

## Lessons learned

- Replace with durable follow-up if needed
