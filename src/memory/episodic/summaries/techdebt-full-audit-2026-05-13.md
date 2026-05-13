---
id: techdebt-full-audit-2026-05-13
title: "\u041F\u043E\u043B\u043D\u044B\u0439 \u0430\u0443\u0434\u0438\u0442 \u0442\
  \u0435\u0445\u0434\u043E\u043B\u0433\u0430 BioETL"
task_id: techdebt-full-audit-2026-05-13
created_at: '2026-05-13T12:32:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: "\u041F\u0440\u043E\u0432\u0435\u0434\u0451\u043D repo-wide \u0430\u0443\u0434\
  \u0438\u0442 \u0442\u0435\u0445\u0434\u043E\u043B\u0433\u0430 \u0438 governance.\
  \ \u041F\u043E\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043D\u044B \u0430\
  \u043A\u0442\u0438\u0432\u043D\u044B\u0435 debt-\u043A\u043B\u0430\u0441\u0442\u0435\
  \u0440\u044B: sanctioned compatibility surface (13 retained entrypoints + legacy\
  \ flat facades), control-plane legacy_observe degraded resume mode, silver filter\
  \ legacy_semantic_silver rollback mode, observability inventory drift (5 dead metrics,\
  \ documented/rule metrics without registry, static cardinality proxy), E2E global\
  \ relaxed DQ env mutation, hotspot pressure \u0432 application/core \u0438 composition\
  \ bootstrap/runtime, stale domain purity allowlist residue. \u041F\u043E\u0434\u0442\
  \u0432\u0435\u0440\u0436\u0434\u0435\u043D\u044B \u0437\u0435\u043B\u0451\u043D\u044B\
  \u0435 \u0437\u043E\u043D\u044B: 0 coarse layer violations, empty bronze fixture\
  \ gaps, empty deprecated gold contract inventory, canonical pytest config, explicit\
  \ integration DQ fixtures, deterministic E2E replay helpers."
---

# Episodic summary

## Task

- Title: Полный аудит техдолга BioETL

## Outcome

- Проведён repo-wide аудит техдолга и governance. Подтверждены активные debt-кластеры: sanctioned compatibility surface (13 retained entrypoints + legacy flat facades), control-plane legacy_observe degraded resume mode, silver filter legacy_semantic_silver rollback mode, observability inventory drift (5 dead metrics, documented/rule metrics without registry, static cardinality proxy), E2E global relaxed DQ env mutation, hotspot pressure в application/core и composition bootstrap/runtime, stale domain purity allowlist residue. Подтверждены зелёные зоны: 0 coarse layer violations, empty bronze fixture gaps, empty deprecated gold contract inventory, canonical pytest config, explicit integration DQ fixtures, deterministic E2E replay helpers.

## Lessons learned

- Replace with durable follow-up if needed
