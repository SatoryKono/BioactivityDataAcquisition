---
id: fix-composite-canonical-surfaces-doc-scan-timeout-20260526
title: Fix composite canonical surfaces doc scan timeout
task_id: fix-composite-canonical-surfaces-doc-scan-timeout-20260526
created_at: '2026-05-26T04:27:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_composite_canonical_surfaces.py
summary: Updated composite canonical surface architecture docs scan to prefer bounded
  git grep over recursive doc file enumeration and chunked stream reads. The grep
  path uses repo-relative pathspecs, fixed-string deprecated symbol matching, legacy
  path filtering, and temporary-file stdout capture to avoid Windows/PyCharm stream-read
  hangs on Google Drive-backed worktrees.
---

# Episodic summary

## Task

- Title: Fix composite canonical surfaces doc scan timeout

## Outcome

- Updated composite canonical surface architecture docs scan to prefer bounded git grep over recursive doc file enumeration and chunked stream reads. The grep path uses repo-relative pathspecs, fixed-string deprecated symbol matching, legacy path filtering, and temporary-file stdout capture to avoid Windows/PyCharm stream-read hangs on Google Drive-backed worktrees.

## Lessons learned

- Architecture tests that scan active docs or generated graphs should use
  bounded repo-index search before Python file streams on Windows/GDrive
  worktrees; chunked reads can still block inside `stream.read`.
