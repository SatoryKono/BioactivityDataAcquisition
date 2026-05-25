---
id: repro-audit-main-20260525
title: Audit pipeline reproducibility on origin/main
task_id: repro-audit-main-20260525
created_at: '2026-05-25T08:32:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/04-reference/contracts/run-manifest-ledger.md
summary: Audited origin/main reproducibility architecture. Strong manifest/ledger/fingerprint/checkpoint
  model and deterministic serialization exist, but origin/main still allows executable
  manifests without canonical config anchors, allows dirty source_revision_state in
  degraded_observable runs, and keeps lineage publication optional outside strict
  profiles. Exact replay is bounded and semantic-child-run based, not universal same-occurrence
  reproduction.
---

# Episodic summary

## Task

- Title: Audit pipeline reproducibility on origin/main

## Outcome

- Audited origin/main reproducibility architecture. Strong manifest/ledger/fingerprint/checkpoint model and deterministic serialization exist, but origin/main still allows executable manifests without canonical config anchors, allows dirty source_revision_state in degraded_observable runs, and keeps lineage publication optional outside strict profiles. Exact replay is bounded and semantic-child-run based, not universal same-occurrence reproduction.

## Lessons learned

- Replace with durable follow-up if needed
