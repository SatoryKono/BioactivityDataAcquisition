---
id: fix-run-context-contract-identity-20260515
title: Fix RunManifestContractIdentity normalization compatibility in run_context_factory
task_id: fix-run-context-contract-identity-20260515
created_at: '2026-05-15T10:55:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Fixed follow-up regressions: strict replay integration test now sets hard_fail
  checkpoint policy for replay_ready, chembl.molecule contract registry hash was resynced
  to the current normalization profile identity, and semantic drift warning review
  logic no longer suppresses all WEAK inventory warnings.'
---

# Episodic summary

## Task

- Title: Fix RunManifestContractIdentity normalization compatibility in run_context_factory

## Outcome

- Fixed follow-up regressions: strict replay integration test now sets hard_fail checkpoint policy for replay_ready, chembl.molecule contract registry hash was resynced to the current normalization profile identity, and semantic drift warning review logic no longer suppresses all WEAK inventory warnings.

## Lessons learned

- Replace with durable follow-up if needed
