---
id: lazy-exports-install-cached-public-exports-20260604
title: Restore install_cached_public_exports export contract
task_id: lazy-exports-install-cached-public-exports-20260604
created_at: '2026-06-04T10:35:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/lazy_exports.py
summary: Confirmed the ImportError is resolved by the existing local lazy_exports
  facade diff that re-exports install_cached_public_exports from composition._lazy_exports
  and includes it in __all__; verified the targeted architecture and lazy-export tests
  pass.
---

# Episodic summary

## Task

- Title: Restore install_cached_public_exports export contract

## Outcome

- Confirmed the ImportError is resolved by the existing local lazy_exports facade diff that re-exports install_cached_public_exports from composition._lazy_exports and includes it in __all__; verified the targeted architecture and lazy-export tests pass.

## Lessons learned

- Replace with durable follow-up if needed
