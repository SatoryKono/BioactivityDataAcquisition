---
id: fix-control-plane-replay-trend-runbook-routing-20260507
title: Fix Control Plane replay trend runbook routing
task_id: fix-control-plane-replay-trend-runbook-routing-20260507
created_at: '2026-05-07T15:30:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated Control Plane replay trend panels 134 and 135 to use checkpoint-debugging.md
  instead of run-manifest-inspection.md, matching replay/checkpoint docs and alert
  baseline. Extended control-plane dashboard link regression expectations to cover
  both panels. JSON validation, targeted control-plane tests, config tests, rules
  tests, and dashboard inventory passed. Broader visual semantics and dashboard-links
  file-level selectors still show unrelated pre-existing failures in bioetl-dq-v2.
---

# Episodic summary

## Task

- Title: Fix Control Plane replay trend runbook routing

## Outcome

- Updated Control Plane replay trend panels 134 and 135 to use checkpoint-debugging.md instead of run-manifest-inspection.md, matching replay/checkpoint docs and alert baseline. Extended control-plane dashboard link regression expectations to cover both panels. JSON validation, targeted control-plane tests, config tests, rules tests, and dashboard inventory passed. Broader visual semantics and dashboard-links file-level selectors still show unrelated pre-existing failures in bioetl-dq-v2.

## Lessons learned

- Replace with durable follow-up if needed
