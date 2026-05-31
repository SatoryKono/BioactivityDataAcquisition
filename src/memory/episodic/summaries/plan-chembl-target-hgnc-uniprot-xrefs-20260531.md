---
id: plan-chembl-target-hgnc-uniprot-xrefs-20260531
title: "\u041F\u043B\u0430\u043D \u0440\u0435\u0430\u043B\u0438\u0437\u0430\u0446\u0438\
  \u0438 HGNC/UniProt xref projection \u0434\u043B\u044F chembl_target"
task_id: plan-chembl-target-hgnc-uniprot-xrefs-20260531
created_at: '2026-05-31T14:04:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: "\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u043B \u0444\u0430\u043A\u0442\
  \u0438\u0447\u0435\u0441\u043A\u0438\u0439 baseline chembl_target \u0432 target_helpers,\
  \ Target entity, Silver/Gold schemas, Arrow schema, target.yaml, normalization profile\
  \ \u0438 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044E\u0449\u0438\u0445\
  \ tests. \u0421\u0444\u043E\u0440\u043C\u0438\u0440\u043E\u0432\u0430\u043B execution-ready\
  \ \u043F\u043B\u0430\u043D \u0442\u043E\u043B\u044C\u043A\u043E \u0434\u043B\u044F\
  \ \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D\u0438\u044F target_xref_hgnc_ids\
  \ \u0438 target_xref_uniprot_ids; \u043E\u0442\u0434\u0435\u043B\u044C\u043D\u043E\
  \ \u0437\u0430\u0444\u0438\u043A\u0441\u0438\u0440\u043E\u0432\u0430\u043B repo-level\
  \ \u0440\u0430\u0441\u0445\u043E\u0436\u0434\u0435\u043D\u0438\u0435 \u0441 \u0432\
  \u043D\u0435\u0448\u043D\u0438\u043C \u043F\u0440\u0435\u0434\u043F\u043E\u043B\u043E\
  \u0436\u0435\u043D\u0438\u0435\u043C \u043F\u0440\u043E \u0441\u0443\u0449\u0435\
  \u0441\u0442\u0432\u0443\u044E\u0449\u0438\u0439 IUPHAR projection."
---

# Episodic summary

## Task

- Title: План реализации HGNC/UniProt xref projection для chembl_target

## Outcome

- Проверил фактический baseline chembl_target в target_helpers, Target entity, Silver/Gold schemas, Arrow schema, target.yaml, normalization profile и существующих tests. Сформировал execution-ready план только для добавления target_xref_hgnc_ids и target_xref_uniprot_ids; отдельно зафиксировал repo-level расхождение с внешним предположением про существующий IUPHAR projection.

## Lessons learned

- Replace with durable follow-up if needed
