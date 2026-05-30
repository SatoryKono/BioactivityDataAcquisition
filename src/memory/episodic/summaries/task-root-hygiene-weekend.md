---
id: task-root-hygiene-weekend
title: Root hygiene closeout (RH-014..RH-018)
task_id: task-root-hygiene-weekend
created_at: '2026-05-30T07:16:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "\u041F\u0440\u0438\u043C\u0435\u043D\u0435\u043D\u044B \u043F\u0440\u043E\
  \u0432\u0435\u0440\u043A\u0438 RH-014/015/016/017/018: concept root \u0431\u043E\
  \u043B\u044C\u0448\u0435 \u043D\u0435 \u043E\u0442\u0441\u043B\u0435\u0436\u0438\
  \u0432\u0430\u0435\u0442\u0441\u044F, observability-\u043A\u0430\u0440\u0434\u0438\
  \u043D\u0430\u043B\u044C\u043D\u043E\u0441\u0442\u044C \u043D\u0430\u043F\u0440\u0430\
  \u0432\u043B\u0435\u043D\u0430 \u0432 reports/observability/runtime_cardinality_inventory.json,\
  \ compose helpers \u0441\u043E\u043E\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\
  \u044E\u0442 allowlist \u0438 \u0442\u0435\u0441\u0442\u0430\u043C root-hygiene.\
  \ \u0414\u043E\u043F\u043E\u043B\u043D\u0438\u0442\u0435\u043B\u044C\u043D\u043E\
  \ \u0443\u0434\u0430\u043B\u0435\u043D\u044B root-\u0437\u0430\u0433\u043B\u0443\
  \u0448\u043A\u0438 application/domain \u0438\u0437 \u0440\u0430\u0431\u043E\u0447\
  \u0435\u0439 \u0434\u0438\u0440\u0435\u043A\u0442\u043E\u0440\u0438\u0438; \u043F\
  \u0440\u043E\u0432\u0435\u0440\u043A\u0430 check-cleanliness \u043F\u0440\u043E\u0434\
  \u043E\u043B\u0436\u0430\u0435\u0442 \u0443\u043A\u0430\u0437\u044B\u0432\u0430\u0442\
  \u044C \u0438\u0445 \u043A\u0430\u043A \u043D\u0435\u0430\u0432\u0442\u043E\u0440\
  \u0438\u0437\u043E\u0432\u0430\u043D\u043D\u044B\u0435 \u0442\u043E\u043B\u044C\u043A\
  \u043E \u043F\u043E\u0442\u043E\u043C\u0443, \u0447\u0442\u043E \u0438\u043D\u0434\
  \u0435\u043A\u0441 \u0440\u0435\u043F\u043E\u0437\u0438\u0442\u043E\u0440\u0438\u044F\
  \ \u0435\u0449\u0451 \u0441\u043E\u0434\u0435\u0440\u0436\u0438\u0442 \u0438\u0445\
  \ \u0437\u0430\u043F\u0438\u0441\u0438 \u0432 \u044D\u0442\u043E\u0439 \u043F\u0435\
  \u0441\u043E\u0447\u043D\u0438\u0446\u0435."
---

# Episodic summary

## Task

- Title: Root hygiene closeout (RH-014..RH-018)

## Outcome

- Применены проверки RH-014/015/016/017/018: concept root больше не отслеживается, observability-кардинальность направлена в reports/observability/runtime_cardinality_inventory.json, compose helpers соответствуют allowlist и тестам root-hygiene. Дополнительно удалены root-заглушки application/domain из рабочей директории; проверка check-cleanliness продолжает указывать их как неавторизованные только потому, что индекс репозитория ещё содержит их записи в этой песочнице.

## Lessons learned

- Replace with durable follow-up if needed
