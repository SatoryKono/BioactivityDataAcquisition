---
id: fix-issue-5272-closeout-drift
title: "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\u0432\
  \u0430\u0442\u044C issue 5272 closeout"
task_id: fix-issue-5272-closeout-drift
created_at: '2026-06-19T12:57:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/issue-5272-application-core-coverage-closeout.json
summary: "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\
  \u0432\u0430\u043D reports/quality/issue-5272-application-core-coverage-closeout.json\
  \ \u0441 live reports/quality/module-coverage-inventory.json: repo_unmeasured_module_count\
  \ \u043E\u0431\u043D\u043E\u0432\u043B\u0451\u043D \u0441 0 \u0434\u043E 1. \u041F\
  \u0440\u0438\u0447\u0438\u043D\u0430 drift \u2014 live inventory currently reports\
  \ unmeasured bioetl.application.composite._coalesce_policy_support. \u041F\u043E\
  \u043F\u044B\u0442\u043A\u0430 coverage-based artifact refresh \u0431\u044B\u043B\
  \u0430 \u0437\u0430\u0431\u043B\u043E\u043A\u0438\u0440\u043E\u0432\u0430\u043D\u0430\
  \ coverage sqlite data file error \u043D\u0430 mounted checkout (.coverage-sharded\
  \ unavailable)."
---

# Episodic summary

## Task

- Title: Синхронизировать issue 5272 closeout

## Outcome

- Синхронизирован reports/quality/issue-5272-application-core-coverage-closeout.json с live reports/quality/module-coverage-inventory.json: repo_unmeasured_module_count обновлён с 0 до 1. Причина drift — live inventory currently reports unmeasured bioetl.application.composite._coalesce_policy_support. Попытка coverage-based artifact refresh была заблокирована coverage sqlite data file error на mounted checkout (.coverage-sharded unavailable).

## Lessons learned

- Replace with durable follow-up if needed
