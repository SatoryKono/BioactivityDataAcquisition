---
id: compatibility-facade-snapshot-drift
title: Sync compatibility facade measured-only snapshot
task_id: compatibility-facade-snapshot-drift
created_at: '2026-06-01T18:24:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/compatibility_facade_inventory.yaml
summary: Expanded the compatibility measured-only allowlist and ratchet budgets to
  cover the newly shipped underscore re-export shims, then regenerated the compatibility
  facade snapshot so docstring scan, YAML registry, and generated documentation are
  back in sync.
---

# Episodic summary

## Task

- Title: Sync compatibility facade measured-only snapshot

## Outcome

- Expanded the compatibility measured-only allowlist and ratchet budgets to cover the newly shipped underscore re-export shims, then regenerated the compatibility facade snapshot so docstring scan, YAML registry, and generated documentation are back in sync.

## Lessons learned

- Replace with durable follow-up if needed
