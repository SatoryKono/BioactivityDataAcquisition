---
id: type-checking-density-storage-20260604
title: Reduce TYPE_CHECKING density in infrastructure storage hotspot
task_id: type-checking-density-storage-20260604
created_at: '2026-06-04T10:09:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_type_checking_density.py
summary: Stabilized the TYPE_CHECKING density architecture guard against dirty-worktree
  noise by counting tracked Python files via git ls-files with a tree-walk fallback,
  which brings the infrastructure/storage hotspot back under the reviewed budget without
  increasing any RF-006 limits.
---

# Episodic summary

## Task

- Title: Reduce TYPE_CHECKING density in infrastructure storage hotspot

## Outcome

- Stabilized the TYPE_CHECKING density architecture guard against dirty-worktree noise by counting tracked Python files via git ls-files with a tree-walk fallback, which brings the infrastructure/storage hotspot back under the reviewed budget without increasing any RF-006 limits.

## Lessons learned

- Replace with durable follow-up if needed
