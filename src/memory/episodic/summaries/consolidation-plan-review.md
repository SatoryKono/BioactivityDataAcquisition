---
id: consolidation-plan-review
title: Review consolidation campaign plan
task_id: consolidation-plan-review
created_at: '2026-05-29T07:24:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
summary: "\u0421\u0432\u0435\u0440\u043A\u0430 \u043F\u043B\u0430\u043D\u0430 \u043A\
  \u043E\u043D\u0441\u043E\u043B\u0438\u0434a\u0446\u0438\u0438 \u043F\u0440\u043E\
  \u0442\u0438\u0432 \u0442\u0435\u043A\u0443\u0449\u0435\u0433\u043E \u0441\u043E\
  \u0441\u0442\u043E\u044F\u043D\u0438\u044F: \u043F\u043E\u0434\u0442\u0432\u0435\
  \u0440\u0436\u0434\u0435\u043D\u044B \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\
  \u044E\u0449\u0438\u0435 gates \u0438 PR-\u043A\u0430\u043D\u0434\u0438\u0434\u0430\
  \u0442\u044B; \u0432\u044B\u044F\u0432\u043B\u0435\u043D\u044B \u0440\u0430\u0441\
  \u0445\u043E\u0436\u0434\u0435\u043D\u0438\u044F (test_regression_metrics \u043E\
  \u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0435\u043D/\u0432 plan \u043D\u0435\u0432\
  \u0435\u0440\u043D\u043E, \u043E\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\
  \u044E\u0449\u0438\u0435 \u0434\u0438\u0440\u0435\u043A\u0442\u043E\u0440\u0438\u0438\
  \ determinism/idempotency/composite_resume \u043D\u0430 main, .warp/\u0434\u043E\
  \u043A\u0438 runbooks \u0432 \u0442\u0435\u043A\u0443\u0449\u0435\u043C tree \u043D\
  \u0435 \u043F\u0440\u0438\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044E\u0442\
  , \u043F\u0440\u0430\u0432\u0438\u043B\u0430 merge-\u0446\u0435\u043F\u043E\u0447\
  \u043A\u0438 repo \u0441\u0435\u0439\u0447\u0430\u0441 \u0444\u043E\u0440\u043C\u0430\
  \u043B\u044C\u043D\u043E \u043D\u0435 \u0432\u043A\u043B\u044E\u0447\u0435\u043D\
  \u044B)."
---

# Episodic summary

## Task

- Title: Review consolidation campaign plan

## Outcome

- Сверка плана консолидaции против текущего состояния: подтверждены существующие gates и PR-кандидаты; выявлены расхождения (test_regression_metrics отсутствен/в plan неверно, отсутствующие директории determinism/idempotency/composite_resume на main, .warp/доки runbooks в текущем tree не присутствуют, правила merge-цепочки repo сейчас формально не включены).

## Lessons learned

- Replace with durable follow-up if needed
