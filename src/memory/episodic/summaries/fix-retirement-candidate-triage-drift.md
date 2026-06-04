---
id: fix-retirement-candidate-triage-drift
title: Fix retirement candidate triage drift
task_id: fix-retirement-candidate-triage-drift
created_at: '2026-06-04T16:32:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/retirement_candidate_triage.yaml
- reports/quality/dead-code-inventory.json
- configs/quality/debt_scorecard.yaml
summary: Removed stale repo-wide zero-import classification for bioetl.domain.ports.serialization
  after direct test import coverage made it no longer a zero-import candidate. Regenerated
  dead-code inventory JSON/MD to 13 classified candidates and ratcheted retirement
  governance counts in debt_scorecard from 14 to 13 while keeping untriaged zero-import
  budget at 0. Validated retirement triage, debt scorecard, dead-code inventory check,
  and debt governance telemetry guards.
---

# Episodic summary

## Task

- Title: Fix retirement candidate triage drift

## Outcome

- Removed stale repo-wide zero-import classification for bioetl.domain.ports.serialization after direct test import coverage made it no longer a zero-import candidate. Regenerated dead-code inventory JSON/MD to 13 classified candidates and ratcheted retirement governance counts in debt_scorecard from 14 to 13 while keeping untriaged zero-import budget at 0. Validated retirement triage, debt scorecard, dead-code inventory check, and debt governance telemetry guards.

## Lessons learned

- Replace with durable follow-up if needed
