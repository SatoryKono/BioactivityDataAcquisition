---
id: dashboard-ux-pytest-hang
title: Debug dashboard UX freshness pytest startup hang
task_id: dashboard-ux-pytest-hang
created_at: '2026-05-24T16:48:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/extraction_params_support.py
summary: Deferred ChemblAdapter import in extraction_params_support so unrelated pytest
  collection no longer blocks on the ChEMBL adapter import graph.
---

# Episodic summary

## Task

- Title: Debug dashboard UX freshness pytest startup hang

## Outcome

- Deferred ChemblAdapter import in extraction_params_support so unrelated pytest collection no longer blocks on the ChEMBL adapter import graph.

## Lessons learned

- Replace with durable follow-up if needed
