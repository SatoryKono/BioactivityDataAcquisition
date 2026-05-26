---
id: fix-memory-note-open-timeout-daemon-20260526
title: Fix memory note read timeout on Windows
task_id: fix-memory-note-open-timeout-daemon-20260526
created_at: '2026-05-26T05:49:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/notes.py
- tests/unit/memory/test_notes_workflow.py
summary: Replaced memory note parsing's open-only timeout guard with a bounded full-text
  reader running in a daemon thread, added a Git-object fallback for tracked files
  when working-tree reads hang, and added unit regressions proving blocked readers
  do not hold pytest until timeout.
---

# Episodic summary

## Task

- Title: Fix memory note read timeout on Windows

## Outcome

- Replaced memory note parsing's open-only timeout guard with a bounded full-text reader running in a daemon thread, added a Git-object fallback for tracked files when working-tree reads hang, and added unit regressions proving blocked readers do not hold pytest until timeout.

## Lessons learned

- Timeout guards around filesystem access must not use non-daemon threads; a
  blocked network-drive read can otherwise keep pytest alive after the guard
  reports a timeout.
