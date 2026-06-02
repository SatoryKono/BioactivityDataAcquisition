---
id: fix-uuid4-identity-policy-drift
title: Fix uuid4 identity policy allowlist drift
task_id: fix-uuid4-identity-policy-drift
created_at: '2026-06-02T08:41:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/determinism_identity_policy.yaml
summary: 'Updated determinism_identity_policy.yaml to match current reviewed uuid4
  occurrence call sites: renamed stale helper symbols, dropped the removed observability
  row, and added the orphan-row quarantine batch-id seam.'
---

# Episodic summary

## Task

- Title: Fix uuid4 identity policy allowlist drift

## Outcome

- Updated determinism_identity_policy.yaml to match current reviewed uuid4 occurrence call sites: renamed stale helper symbols, dropped the removed observability row, and added the orphan-row quarantine batch-id seam.

## Lessons learned

- Replace with durable follow-up if needed
