---
id: techdebt-implementation-wave-1-2026-05-13
title: "\u0421\u043D\u0438\u0436\u0435\u043D\u0438\u0435 \u0442\u0435\u0445\u0434\u043E\
  \u043B\u0433\u0430 BioETL: wave 1"
task_id: techdebt-implementation-wave-1-2026-05-13
created_at: '2026-05-13T13:07:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: "\u0412\u044B\u043F\u043E\u043B\u043D\u0435\u043D\u0430 \u043F\u0435\u0440\
  \u0432\u0430\u044F \u0432\u043E\u043B\u043D\u0430 \u0441\u043D\u0438\u0436\u0435\
  \u043D\u0438\u044F \u0442\u0435\u0445\u0434\u043E\u043B\u0433\u0430. E2E relaxed\
  \ DQ \u0431\u043E\u043B\u044C\u0448\u0435 \u043D\u0435 \u0432\u043A\u043B\u044E\u0447\
  \u0430\u0435\u0442\u0441\u044F \u0433\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u043E\
  \ \u0438\u0437 tests/e2e/conftest.py: \u0434\u043E\u0431\u0430\u0432\u043B\u0435\
  \u043D\u044B explicit fixtures relaxed_dq_env/strict_dq_env \u0441 cache clear,\
  \ pipeline-heavy E2E \u043C\u043E\u0434\u0443\u043B\u0438 \u043F\u0435\u0440\u0435\
  \u0432\u0435\u0434\u0435\u043D\u044B \u043D\u0430 \u044F\u0432\u043D\u044B\u0439\
  \ pytestmark usefixtures(relaxed_dq_env), helper/policy suites \u0437\u0430\u043A\
  \u0440\u0435\u043F\u043B\u0435\u043D\u044B \u043D\u0430 strict_dq_env, \u0434\u043E\
  \u0431\u0430\u0432\u043B\u0435\u043D architecture guard tests/architecture/test_e2e_dq_fixture_policy.py\
  \ \u043F\u0440\u043E\u0442\u0438\u0432 session-autouse env mutation. \u0412 tests/architecture/test_domain_unit_test_purity.py\
  \ \u0443\u0434\u0430\u043B\u0435\u043D\u044B 14 stale legacy datetime allowlist\
  \ entries \u0438 \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D regression test\
  \ \u043F\u0440\u043E\u0442\u0438\u0432 \u0438\u0445 \u0432\u043E\u0437\u0432\u0440\
  \u0430\u0442\u0430. \u041F\u0440\u043E\u0432\u0435\u0440\u043A\u0438: architecture\
  \ suite \u0434\u043B\u044F purity/e2e DQ policy, e2e helper suites, collect-only\
  \ \u0434\u043B\u044F pubchem E2E \u2014 \u0432\u0441\u0435 \u0437\u0435\u043B\u0451\
  \u043D\u044B\u0435."
---

# Episodic summary

## Task

- Title: Снижение техдолга BioETL: wave 1

## Outcome

- Выполнена первая волна снижения техдолга. E2E relaxed DQ больше не включается глобально из tests/e2e/conftest.py: добавлены explicit fixtures relaxed_dq_env/strict_dq_env с cache clear, pipeline-heavy E2E модули переведены на явный pytestmark usefixtures(relaxed_dq_env), helper/policy suites закреплены на strict_dq_env, добавлен architecture guard tests/architecture/test_e2e_dq_fixture_policy.py против session-autouse env mutation. В tests/architecture/test_domain_unit_test_purity.py удалены 14 stale legacy datetime allowlist entries и добавлен regression test против их возврата. Проверки: architecture suite для purity/e2e DQ policy, e2e helper suites, collect-only для pubchem E2E — все зелёные.

## Lessons learned

- Replace with durable follow-up if needed
