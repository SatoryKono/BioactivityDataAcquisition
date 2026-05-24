---
id: implement-rf009-historical-exact-replay-20260524
title: Implement historical exact replay evidence guard
task_id: implement-rf009-historical-exact-replay-20260524
created_at: '2026-05-24T13:29:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/run_historical_replay_universe_campaign.py
summary: 'Implemented RF-009 bounded fail-closed guard for universal historical exact-replay
  wording. Updated standalone QA campaign and bioetl run-manifest universe-report
  so --require-universal-claim requires governed_full_corpus_gate.satisfied=true,
  exposed governed_full_corpus_gate in the campaign JSON payload, added policy/script/CLI
  unit tests, and synced docs/04-reference/contracts/run-manifest-ledger.md wording.
  Verification: ruff format/check passed on impacted Python files; targeted pytest
  passed for universe policy, script helper, CLI helper, existing universe service
  tests, and reproducibility docs drift.'
---

# Episodic summary

## Task

- Title: Implement historical exact replay evidence guard

## Outcome

- Implemented RF-009 bounded fail-closed guard for universal historical exact-replay wording. Updated standalone QA campaign and bioetl run-manifest universe-report so --require-universal-claim requires governed_full_corpus_gate.satisfied=true, exposed governed_full_corpus_gate in the campaign JSON payload, added policy/script/CLI unit tests, and synced docs/04-reference/contracts/run-manifest-ledger.md wording. Verification: ruff format/check passed on impacted Python files; targeted pytest passed for universe policy, script helper, CLI helper, existing universe service tests, and reproducibility docs drift.

## Lessons learned

- Replace with durable follow-up if needed
