---
id: memory-note-timeout-validation-fix
title: Fix memory note timeout validation regression
task_id: memory-note-timeout-validation-fix
created_at: '2026-05-26T14:18:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/notes.py
summary: Restored monkeypatchable note-read timeouts and switched episodic memory
  scaffold validation to a metadata-only path so timeout-sensitive note tests and
  body-skip validation tests pass again.
---

# Episodic summary

## Task

- Title: Fix memory note timeout validation regression

## Outcome

- Restored monkeypatchable note-read timeouts and switched episodic memory scaffold validation to a metadata-only path so timeout-sensitive note tests and body-skip validation tests pass again.

## Lessons learned

- Replace with durable follow-up if needed
