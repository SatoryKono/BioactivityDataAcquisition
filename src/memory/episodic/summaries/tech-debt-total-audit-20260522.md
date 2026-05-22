---
id: tech-debt-total-audit-20260522
title: "\u041F\u043E\u043B\u043D\u044B\u0439 \u0430\u0443\u0434\u0438\u0442 \u0442\
  \u0435\u0445\u043D\u0438\u0447\u0435\u0441\u043A\u043E\u0433\u043E \u0434\u043E\u043B\
  \u0433\u0430 BioETL"
task_id: tech-debt-total-audit-20260522
created_at: '2026-05-22T09:20:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Completed full technical debt audit. Key findings: sanctioned compatibility/public
  entrypoint surface remains large (14 entrypoints, 20 twin pairs, 67 config-root
  importers); dead-code governance uses fail-fast no-growth but repo-wide zero-import
  candidates remain only partially triaged; hotspot duplication remains in application/core,
  composition/bootstrap/runtime, application/services/control_plane, composition/runtime_builders;
  config compatibility aliases are bounded but still active; fixture/VCR replay debt
  is currently zero; module coverage inventory lacks coverage.xml backing; observability
  cardinality evidence is governed but noisy due alias emitter extraction.'
---

# Episodic summary

## Task

- Title: Полный аудит технического долга BioETL

## Outcome

- Completed full technical debt audit. Key findings: sanctioned compatibility/public entrypoint surface remains large (14 entrypoints, 20 twin pairs, 67 config-root importers); dead-code governance uses fail-fast no-growth but repo-wide zero-import candidates remain only partially triaged; hotspot duplication remains in application/core, composition/bootstrap/runtime, application/services/control_plane, composition/runtime_builders; config compatibility aliases are bounded but still active; fixture/VCR replay debt is currently zero; module coverage inventory lacks coverage.xml backing; observability cardinality evidence is governed but noisy due alias emitter extraction.

## Lessons learned

- Replace with durable follow-up if needed
