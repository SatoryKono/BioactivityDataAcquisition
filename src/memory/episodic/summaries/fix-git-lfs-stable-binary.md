---
id: fix-git-lfs-stable-binary
title: Move Git LFS filter binary out of volatile cache
task_id: fix-git-lfs-stable-binary
created_at: '2026-06-16T06:31:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- .git/config
- .git/hooks/pre-push
summary: Installed git-lfs 3.7.1 into /home/fedor/.local/bin, restored repository
  LFS filters to canonical git-lfs clean/smudge/filter-process commands, removed local
  alias override, restored hooks to PATH-based git-lfs invocation, and verified git
  lfs env/status pass without .cache or /tmp filter paths.
---

# Episodic summary

## Task

- Title: Move Git LFS filter binary out of volatile cache

## Outcome

- Installed git-lfs 3.7.1 into /home/fedor/.local/bin, restored repository LFS filters to canonical git-lfs clean/smudge/filter-process commands, removed local alias override, restored hooks to PATH-based git-lfs invocation, and verified git lfs env/status pass without .cache or /tmp filter paths.

## Lessons learned

- Replace with durable follow-up if needed
