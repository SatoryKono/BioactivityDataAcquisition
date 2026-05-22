---
id: doctor-check
title: Run project doctor
task_id: doctor-check
created_at: '2026-05-22T07:58:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/health.py
summary: Mapped doctor to canonical health/diagnostics surfaces, ran observability
  contract checks, and confirmed health command timed out during heavy startup/import
  path before yielding provider status.
---

# Episodic summary

## Task

- Title: Run project doctor

## Outcome

- Mapped doctor to canonical health/diagnostics surfaces, ran observability contract checks, and confirmed health command timed out during heavy startup/import path before yielding provider status.

## Lessons learned

- Replace with durable follow-up if needed
