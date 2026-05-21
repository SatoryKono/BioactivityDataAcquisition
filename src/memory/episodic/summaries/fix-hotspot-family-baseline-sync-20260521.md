---
id: fix-hotspot-family-baseline-sync-20260521
title: Fix hotspot family baseline sync drift
task_id: fix-hotspot-family-baseline-sync-20260521
created_at: '2026-05-21T08:20:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/dev/pretest_guardrails.sh
- configs/quality/debt_scorecard.yaml
- reports/quality/hotspot-family-baseline.json
summary: Removed active-only hotspot baseline guardrail drift, synchronized reviewed-baseline
  scorecard metrics, and regenerated hotspot family baseline artifacts with passing
  targeted architecture and generator checks.
---

# Episodic summary

## Task

- Title: Fix hotspot family baseline sync drift

## Outcome

- Removed active-only hotspot baseline guardrail drift, synchronized reviewed-baseline scorecard metrics, and regenerated hotspot family baseline artifacts with passing targeted architecture and generator checks.

## Lessons learned

- Replace with durable follow-up if needed
