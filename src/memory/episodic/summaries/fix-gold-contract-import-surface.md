---
id: fix-gold-contract-import-surface
title: Fix gold contracts import surface for contract pytest startup
task_id: fix-gold-contract-import-surface
created_at: '2026-06-15T11:19:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Validated that gold contract import surface is currently healthy on both
  WSL and Windows interpreters; contract test collection with --network now succeeds,
  so the previous ImportError for GOLD_CONTRACT_VERSION_UNKNOWN is no longer reproducible
  in the current worktree.
---

# Episodic summary

## Task

- Title: Fix gold contracts import surface for contract pytest startup

## Outcome

- Validated that gold contract import surface is currently healthy on both WSL and Windows interpreters; contract test collection with --network now succeeds, so the previous ImportError for GOLD_CONTRACT_VERSION_UNKNOWN is no longer reproducible in the current worktree.

## Lessons learned

- Replace with durable follow-up if needed
