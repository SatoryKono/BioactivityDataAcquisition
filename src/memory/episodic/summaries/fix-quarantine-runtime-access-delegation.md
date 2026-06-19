---
id: fix-quarantine-runtime-access-delegation
title: "\u0412\u043E\u0441\u0441\u0442\u0430\u043D\u043E\u0432\u0438\u0442\u044C delegation\
  \ quarantine runtime access"
task_id: fix-quarantine-runtime-access-delegation
created_at: '2026-06-19T11:32:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/cli/commands/domains/quarantine/test_runtime_access.py
summary: "\u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0430 \u043F\u043E\u043A\u0430\
  \u0437\u0430\u043B\u0430, \u0447\u0442\u043E \u043D\u0430 \u0442\u0435\u043A\u0443\
  \u0449\u0435\u043C checkout delegation quarantine runtime access \u0443\u0436\u0435\
  \ \u0440\u0430\u0431\u043E\u0442\u0430\u0435\u0442 \u043A\u043E\u0440\u0440\u0435\
  \u043A\u0442\u043D\u043E: patch \u043D\u0430 bioetl.composition.health_api.get_quarantine_runtime_service/get_quarantine_service\
  \ \u043F\u0435\u0440\u0435\u0445\u0432\u0430\u0442\u044B\u0432\u0430\u0435\u0442\
  \u0441\u044F, \u0430 tests/unit/interfaces/cli/commands/domains/quarantine/test_runtime_access.py\
  \ \u043F\u0440\u043E\u0445\u043E\u0434\u0438\u0442 \u0431\u0435\u0437 \u043F\u0440\
  \u0430\u0432\u043E\u043A."
---

# Episodic summary

## Task

- Title: Восстановить delegation quarantine runtime access

## Outcome

- Проверка показала, что на текущем checkout delegation quarantine runtime access уже работает корректно: patch на bioetl.composition.health_api.get_quarantine_runtime_service/get_quarantine_service перехватывается, а tests/unit/interfaces/cli/commands/domains/quarantine/test_runtime_access.py проходит без правок.

## Lessons learned

- Replace with durable follow-up if needed
