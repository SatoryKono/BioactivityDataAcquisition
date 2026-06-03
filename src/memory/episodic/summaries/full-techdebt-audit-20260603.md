---
id: full-techdebt-audit-20260603
title: Full BioETL technical debt audit
task_id: full-techdebt-audit-20260603
created_at: '2026-06-03T17:17:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Audited BioETL technical debt and debt governance. Confirmed strong enforcement
  for contracts, replay/idempotency, VCR, DQ, and metric governance; no direct layer
  leakage found. Main residual debt is sanctioned compatibility/public-facade burden,
  legacy flat facades, large control-plane and observability hotspots, runtime-vs-CLI
  seam sprawl, and compatibility-test maintenance overhead.
---

# Episodic summary

## Task

- Title: Full BioETL technical debt audit

## Outcome

- Audited BioETL technical debt and debt governance. Confirmed strong enforcement for contracts, replay/idempotency, VCR, DQ, and metric governance; no direct layer leakage found. Main residual debt is sanctioned compatibility/public-facade burden, legacy flat facades, large control-plane and observability hotspots, runtime-vs-CLI seam sprawl, and compatibility-test maintenance overhead.

## Lessons learned

- Replace with durable follow-up if needed
