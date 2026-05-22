---
id: architecture-review-20260522-current
title: Architecture review and refactoring roadmap
task_id: architecture-review-20260522-current
created_at: '2026-05-22T11:53:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Completed read-only architecture review of current dirty working tree. Used
  parallel explorer agents, primary py-audit-bot style audit, and sequential double-check
  audit. Integral score around 7.55/10 WARN. Key findings: no layer policy violations
  but dependency-map generated artifacts drift and cross-layer edge budget exceeds
  331; replay-critical checkpoint helpers still fallback to current_utc_time when
  ClockPort omitted; domain/context.py deep port import exposes facade-rule enforcement
  gap; hotspot/test debt is governed but material; ADR/runtime metadata drift remains.
  No implementation changes requested or made.'
---

# Episodic summary

## Task

- Title: Architecture review and refactoring roadmap

## Outcome

- Completed read-only architecture review of current dirty working tree. Used parallel explorer agents, primary py-audit-bot style audit, and sequential double-check audit. Integral score around 7.55/10 WARN. Key findings: no layer policy violations but dependency-map generated artifacts drift and cross-layer edge budget exceeds 331; replay-critical checkpoint helpers still fallback to current_utc_time when ClockPort omitted; domain/context.py deep port import exposes facade-rule enforcement gap; hotspot/test debt is governed but material; ADR/runtime metadata drift remains. No implementation changes requested or made.

## Lessons learned

- Replace with durable follow-up if needed
