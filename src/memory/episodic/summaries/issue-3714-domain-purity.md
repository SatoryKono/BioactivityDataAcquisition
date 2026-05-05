---
id: issue-3714-domain-purity
title: Enforce Domain layer contains no infrastructure dependencies
task_id: issue-3714-domain-purity
created_at: '2026-05-05T14:27:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_domain_no_infrastructure_dependencies.py
summary: Added an architecture ratchet that forbids direct and dynamic domain imports
  of bioetl.infrastructure, including TYPE_CHECKING-only imports.
---

# Episodic summary

## Task

- Title: Enforce Domain layer contains no infrastructure dependencies

## Outcome

- Added an architecture ratchet that forbids direct and dynamic domain imports of bioetl.infrastructure, including TYPE_CHECKING-only imports.

## Lessons learned

- Replace with durable follow-up if needed
