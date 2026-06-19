---
id: fix-fixture-duplication-artifact-order
title: "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0438\u0440\u043E\u0432\
  \u0430\u0442\u044C fixture duplication artifact order"
task_id: fix-fixture-duplication-artifact-order
created_at: '2026-06-19T14:40:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/test-fixture-asset-duplication.json
summary: "\u041F\u0435\u0440\u0435\u0441\u043E\u0431\u0440\u0430\u043D reports/quality/test-fixture-asset-duplication.json\
  \ \u0448\u0442\u0430\u0442\u043D\u044B\u043C scripts.engineering.qa.report_test_governance_audit\
  \ writer. \u0418\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u0435 \u0431\u044B\u043B\
  \u043E \u0434\u0435\u0442\u0435\u0440\u043C\u0438\u043D\u0438\u0440\u043E\u0432\u0430\
  \u043D\u043D\u044B\u043C: \u0441\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\
  \u0438\u0440\u043E\u0432\u0430\u043D \u043F\u043E\u0440\u044F\u0434\u043E\u043A\
  \ paths \u0432\u043D\u0443\u0442\u0440\u0438 duplicate group \u0434\u043B\u044F\
  \ Chembl VCR duplicate hash, \u043F\u043E\u0441\u043B\u0435 \u0447\u0435\u0433\u043E\
  \ \u0430\u0440\u0445\u0438\u0442\u0435\u043A\u0442\u0443\u0440\u043D\u044B\u0439\
  \ governance test \u0441\u043D\u043E\u0432\u0430 \u043F\u0440\u043E\u0445\u043E\u0434\
  \u0438\u0442."
---

# Episodic summary

## Task

- Title: Синхронизировать fixture duplication artifact order

## Outcome

- Пересобран reports/quality/test-fixture-asset-duplication.json штатным scripts.engineering.qa.report_test_governance_audit writer. Изменение было детерминированным: синхронизирован порядок paths внутри duplicate group для Chembl VCR duplicate hash, после чего архитектурный governance test снова проходит.

## Lessons learned

- Replace with durable follow-up if needed
