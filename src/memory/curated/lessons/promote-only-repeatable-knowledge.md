---
id: promote-only-repeatable-knowledge
title: Promote only repeatable knowledge
kind: lesson
source_refs:
- src/memory/README.md
- src/memory/DAILY_WORKFLOW.md
- docs/00-project/ai/agents/guides/MEMORY_USAGE.md
- src/memory/tooling/workflow.py
confidence: curated
last_verified: '2026-08-04T00:00:00Z'
summary: Promote notes only when the knowledge is reusable across future tasks and leave one-off debug detail in episodic memory.
---

# Lesson

## Observation

- Curated memory loses value quickly when one-off debugging details are promoted without durable reuse potential.
- Short-lived task context belongs in episodic memory until the pattern repeats or becomes a stable engineering rule.

## Reuse guidance

- Promote a note only when it captures an architectural constraint, recurring operational response, or domain rule that will help future tasks.
- Prefer leaving narrow task details in episodic memory and pruning them on schedule instead of promoting them by default.
