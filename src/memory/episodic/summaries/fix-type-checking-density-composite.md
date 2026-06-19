---
id: fix-type-checking-density-composite
title: "\u0421\u043D\u0438\u0436\u0435\u043D\u0438\u0435 TYPE_CHECKING density \u0432\
  \ composite"
task_id: fix-type-checking-density-composite
created_at: '2026-06-19T10:56:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/composite/_coalesce_policy_support.py
summary: "\u0423\u0431\u0440\u0430\u043D \u043B\u0438\u0448\u043D\u0438\u0439 TYPE_CHECKING\
  \ block \u0438\u0437 application/composite/_coalesce_policy_support.py, \u0432\u0432\
  \u0435\u0434\u0451\u043D\u043D\u044B\u0439 \u043F\u0440\u0435\u0434\u044B\u0434\u0443\
  \u0449\u0438\u043C LOC-\u0440\u0435\u0444\u0430\u043A\u0442\u043E\u0440\u0438\u043D\
  \u0433\u043E\u043C. \u0410\u0440\u0445\u0438\u0442\u0435\u043A\u0442\u0443\u0440\
  \u043D\u044B\u0439 budget test \u043F\u043E hotspot application/composite \u0441\
  \u043D\u043E\u0432\u0430 \u043F\u0440\u043E\u0445\u043E\u0434\u0438\u0442; composite\
  \ unit smoke \u043E\u0441\u0442\u0430\u0451\u0442\u0441\u044F \u0437\u0435\u043B\
  \u0451\u043D\u044B\u043C."
---

# Episodic summary

## Task

- Title: Снижение TYPE_CHECKING density в composite

## Outcome

- Убран лишний TYPE_CHECKING block из application/composite/_coalesce_policy_support.py, введённый предыдущим LOC-рефакторингом. Архитектурный budget test по hotspot application/composite снова проходит; composite unit smoke остаётся зелёным.

## Lessons learned

- Replace with durable follow-up if needed
