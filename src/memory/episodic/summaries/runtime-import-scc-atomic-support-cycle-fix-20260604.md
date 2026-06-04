---
id: runtime-import-scc-atomic-support-cycle-fix-20260604
title: Fix atomic support SCC
task_id: runtime-import-scc-atomic-support-cycle-fix-20260604
created_at: '2026-06-04T11:15:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Removed the runtime import cycle between storage.support.atomic_group and
  atomic_ops by replacing the AtomicWriteGroup re-export in atomic_ops with a lazy
  importlib-backed __getattr__. Verified the SCC guard now passes and the compatibility
  import from atomic_ops still resolves AtomicWriteGroup correctly. Module-coverage
  hash refresh was not completed because reports/coverage/coverage.xml is currently
  unavailable and source_tree_sha256 has been unstable on the shared-drive worktree.
---

# Episodic summary

## Task

- Title: Fix atomic support SCC

## Outcome

- Removed the runtime import cycle between storage.support.atomic_group and atomic_ops by replacing the AtomicWriteGroup re-export in atomic_ops with a lazy importlib-backed __getattr__. Verified the SCC guard now passes and the compatibility import from atomic_ops still resolves AtomicWriteGroup correctly. Module-coverage hash refresh was not completed because reports/coverage/coverage.xml is currently unavailable and source_tree_sha256 has been unstable on the shared-drive worktree.

## Lessons learned

- Replace with durable follow-up if needed
