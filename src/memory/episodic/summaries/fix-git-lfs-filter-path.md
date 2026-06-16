---
id: fix-git-lfs-filter-path
title: Fix stale Git LFS filter path
task_id: fix-git-lfs-filter-path
created_at: '2026-06-16T06:22:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- .git/config
- .git/hooks/pre-push
- .cache/git-lfs/git-lfs
summary: Restored local Git LFS by copying git-lfs 3.7.1 to .cache/git-lfs/git-lfs,
  updating local filter.lfs clean/smudge/process and alias.lfs to that binary, and
  rewriting local Git hooks to call it directly; git lfs env/status now work without
  PATH git-lfs.
---

# Episodic summary

## Task

- Title: Fix stale Git LFS filter path

## Outcome

- Restored local Git LFS by copying git-lfs 3.7.1 to .cache/git-lfs/git-lfs, updating local filter.lfs clean/smudge/process and alias.lfs to that binary, and rewriting local Git hooks to call it directly; git lfs env/status now work without PATH git-lfs.

## Lessons learned

- Replace with durable follow-up if needed
