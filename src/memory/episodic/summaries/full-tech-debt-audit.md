---
id: full-tech-debt-audit
title: Full technical debt and debt governance audit
task_id: full-tech-debt-audit
created_at: '2026-05-24T12:25:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Audited BioETL technical debt governance, compatibility facades, duplication
  hotspots, determinism policies, config/contract compatibility, test enforcement
  gaps, and observability governance. Confirmed zero explicit transition-debt budget
  but significant retained public facades, legacy tuple/bootstrap compatibility, duplication
  concentrated in control-plane/runtime builders, documented replay/hash compatibility
  aliases, selective golden-master coverage, three remaining architecture skipif tests,
  and heuristic-only cardinality review. Validated a focused architecture test slice
  passed.
---

# Episodic summary

## Task

- Title: Full technical debt and debt governance audit

## Outcome

- Audited BioETL technical debt governance, compatibility facades, duplication hotspots, determinism policies, config/contract compatibility, test enforcement gaps, and observability governance. Confirmed zero explicit transition-debt budget but significant retained public facades, legacy tuple/bootstrap compatibility, duplication concentrated in control-plane/runtime builders, documented replay/hash compatibility aliases, selective golden-master coverage, three remaining architecture skipif tests, and heuristic-only cardinality review. Validated a focused architecture test slice passed.

## Lessons learned

- Replace with durable follow-up if needed
