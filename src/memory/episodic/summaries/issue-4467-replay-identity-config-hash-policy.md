---
id: issue-4467-replay-identity-config-hash-policy
title: Issue 4467 replay identity and config hash policy
task_id: issue-4467-replay-identity-config-hash-policy
created_at: '2026-05-21T17:52:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4467
summary: 'Closed GitHub issue #4467 after verifying deterministic identity governance.
  Added a focused RunManifestInspectionService diff regression proving legacy config_hash-only
  divergence remains noncanonical while shared execution_fingerprint and effective-config
  anchors preserve semantic_equivalent_replay. Targeted architecture, runtime SCC,
  run-manifest, contract, ruff, and diff whitespace checks passed.'
---

# Episodic summary

## Task

- Title: Issue 4467 replay identity and config hash policy

## Outcome

- Closed GitHub issue #4467 after verifying deterministic identity governance. Added a focused RunManifestInspectionService diff regression proving legacy config_hash-only divergence remains noncanonical while shared execution_fingerprint and effective-config anchors preserve semantic_equivalent_replay. Targeted architecture, runtime SCC, run-manifest, contract, ruff, and diff whitespace checks passed.

## Lessons learned

- Replace with durable follow-up if needed
