---
id: git-lfs-push-gh008
title: resolve-git-lfs-push-rejection
task_id: git-lfs-push-gh008
created_at: '2026-05-24T17:16:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Diagnosed GH008 unknown Git LFS objects on push. Installed a verified temporary
  git-lfs 3.7.1 binary under /tmp because system git-lfs was unavailable and sudo
  was not available. Confirmed LFS fsck OK and mapped rejected OIDs to OpenAlex rf013
  health cassettes. Dry-run with GIT_LFS_SKIP_LOCKS_VERIFY=1 enumerated the missing
  objects, but actual LFS upload could not authenticate in this WSL environment because
  GitHub credentials/token were unavailable.
---

# Episodic summary

## Task

- Title: resolve-git-lfs-push-rejection

## Outcome

- Diagnosed GH008 unknown Git LFS objects on push. Installed a verified temporary git-lfs 3.7.1 binary under /tmp because system git-lfs was unavailable and sudo was not available. Confirmed LFS fsck OK and mapped rejected OIDs to OpenAlex rf013 health cassettes. Dry-run with GIT_LFS_SKIP_LOCKS_VERIFY=1 enumerated the missing objects, but actual LFS upload could not authenticate in this WSL environment because GitHub credentials/token were unavailable.

## Lessons learned

- Replace with durable follow-up if needed
