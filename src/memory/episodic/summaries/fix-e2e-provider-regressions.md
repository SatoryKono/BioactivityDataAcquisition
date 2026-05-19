---
id: fix-e2e-provider-regressions
title: Fix provider E2E regressions for PubMed, Semantic Scholar, and UniProt
task_id: fix-e2e-provider-regressions
created_at: '2026-05-18T19:12:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/_dq_config_normalization.py
- tests/unit/infrastructure/config/test_dq_config_loader.py
summary: Fixed DQ config normalization so legacy allowed_values aliases populate runtime
  enum rules; added loader regression test; verified PubMed publication identifier
  E2E plus Semantic Scholar and UniProt protein E2E all pass.
---

# Episodic summary

## Task

- Title: Fix provider E2E regressions for PubMed, Semantic Scholar, and UniProt

## Outcome

- Fixed DQ config normalization so legacy allowed_values aliases populate runtime enum rules; added loader regression test; verified PubMed publication identifier E2E plus Semantic Scholar and UniProt protein E2E all pass.

## Lessons learned

- Replace with durable follow-up if needed
