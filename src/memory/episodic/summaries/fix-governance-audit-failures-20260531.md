---
id: fix-governance-audit-failures-20260531
title: "\u0418\u0441\u043F\u0440\u0430\u0432\u043B\u0435\u043D\u0438\u0435 \u0443\u043F\
  \u0430\u0432\u0448\u0438\u0445 governance/regression \u0442\u0435\u0441\u0442\u043E\
  \u0432"
task_id: fix-governance-audit-failures-20260531
created_at: '2026-05-31T13:34:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: "\u041E\u0431\u043D\u043E\u0432\u0438\u043B governance inventories \u0434\
  \u043B\u044F oversized test modules \u0438 runtime UUID seams, \u043F\u0435\u0440\
  \u0435\u0441\u043E\u0431\u0440\u0430\u043B docs/filters inventory baseline, \u0438\
  \u0441\u043F\u0440\u0430\u0432\u0438\u043B \u0442\u0440\u0438 ruff-\u0440\u0435\u0433\
  \u0440\u0435\u0441\u0441\u0438\u0438 \u0432 fetch forwarding, manifest diagnostics\
  \ imports \u0438 run ledger fsync helper; \u0442\u0430\u0440\u0433\u0435\u0442\u0438\
  \u0440\u043E\u0432\u0430\u043D\u043D\u044B\u0435 architecture/regression \u0442\u0435\
  \u0441\u0442\u044B \u0437\u0435\u043B\u0451\u043D\u044B\u0435, ruff check src/bioetl\
  \ \u0437\u0435\u043B\u0451\u043D\u044B\u0439."
---

# Episodic summary

## Task

- Title: Исправление упавших governance/regression тестов

## Outcome

- Обновил governance inventories для oversized test modules и runtime UUID seams, пересобрал docs/filters inventory baseline, исправил три ruff-регрессии в fetch forwarding, manifest diagnostics imports и run ledger fsync helper; таргетированные architecture/regression тесты зелёные, ruff check src/bioetl зелёный.

## Lessons learned

- Replace with durable follow-up if needed
