---
id: observability-audit-chembl-assay-20260508
title: Observability audit for chembl_assay workflow
task_id: observability-audit-chembl-assay-20260508
created_at: '2026-05-08T18:37:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Ran chembl_assay workflow limit 10000; success; known alias defects A-D not
  reproduced; DQ disabled semantics correct; Loki works; Tempo empty expected with
  NoOpTracing; real defects in Runtime Error Rate query semantics and Silver Reject
  Explorer backend/compose contract.
---

# Episodic summary

## Task

- Title: Observability audit for chembl_assay workflow

## Outcome

- Ran chembl_assay workflow limit 10000; success; known alias defects A-D not reproduced; DQ disabled semantics correct; Loki works; Tempo empty expected with NoOpTracing; real defects in Runtime Error Rate query semantics and Silver Reject Explorer backend/compose contract.

## Lessons learned

- Replace with durable follow-up if needed
