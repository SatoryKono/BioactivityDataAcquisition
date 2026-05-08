---
id: fix-architecture-domain-complexity-default-registry-lines-20260508
title: Fix architecture domain complexity and registry line cap
task_id: fix-architecture-domain-complexity-default-registry-lines-20260508
created_at: '2026-05-08T14:22:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/workflow/config.py
- src/bioetl/composition/providers/_default_registry.py
summary: Reduced run_type_context cyclomatic complexity to the domain threshold by
  replacing explicit loop branching with a single next-based lookup; kept _default_registry.py
  below the Wave 3 line cap by simplifying the private protocol signature. Verified
  targeted architecture and related unit tests.
---

# Episodic summary

## Task

- Title: Fix architecture domain complexity and registry line cap

## Outcome

- Reduced run_type_context cyclomatic complexity to the domain threshold by replacing explicit loop branching with a single next-based lookup; kept _default_registry.py below the Wave 3 line cap by simplifying the private protocol signature. Verified targeted architecture and related unit tests.

## Lessons learned

- Replace with durable follow-up if needed
