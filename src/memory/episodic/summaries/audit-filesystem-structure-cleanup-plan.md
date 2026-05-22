---
id: audit-filesystem-structure-cleanup-plan
title: Audit filesystem structure and cleanup plan
task_id: audit-filesystem-structure-cleanup-plan
created_at: '2026-05-22T19:03:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Completed architecture-strict filesystem audit of BioETL root/configs/tests/docs/reports/data
  surfaces. Established that src/bioetl, src/memory, configs, tests/fixtures, reports,
  docs/reports, docs/99-archive, and data are governance-sensitive and not blanket
  cleanup targets. Confirmed TTL-governed transient subclasses under reports/quality
  for _tmp_* and pretest_guardrails_*.json. Identified local-only cache/env/tooling
  roots and root-level review candidate tests.txt as primary cleanup concerns. Produced
  deterministic phased cleanup plan with SAFE, REVIEW_REQUIRED, and BLOCKED lanes.
---

# Episodic summary

## Task

- Title: Audit filesystem structure and cleanup plan

## Outcome

- Completed architecture-strict filesystem audit of BioETL root/configs/tests/docs/reports/data surfaces. Established that src/bioetl, src/memory, configs, tests/fixtures, reports, docs/reports, docs/99-archive, and data are governance-sensitive and not blanket cleanup targets. Confirmed TTL-governed transient subclasses under reports/quality for _tmp_* and pretest_guardrails_*.json. Identified local-only cache/env/tooling roots and root-level review candidate tests.txt as primary cleanup concerns. Produced deterministic phased cleanup plan with SAFE, REVIEW_REQUIRED, and BLOCKED lanes.

## Lessons learned

- Replace with durable follow-up if needed
