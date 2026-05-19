---
id: chembl-contract-registry-hash-fix-20260519
title: "\u0421\u0438\u043D\u0445\u0440\u043E\u043D\u0438\u0437\u0430\u0446\u0438\u044F\
  \ hash \u0432 ChEMBL contract registry"
task_id: chembl-contract-registry-hash-fix-20260519
created_at: '2026-05-19T03:29:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "\u041E\u0431\u043D\u043E\u0432\u043B\u0435\u043D normalization_profile_hash\
  \ \u0434\u043B\u044F chembl.assay \u0432 configs/base/contract_registry.yaml \u043F\
  \u043E\u0441\u043B\u0435 \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F\
  \ canonical Silver seam \u043D\u0430 assay_description; registry \u0441\u043D\u043E\
  \u0432\u0430 \u0441\u043E\u0432\u043F\u0430\u0434\u0430\u0435\u0442 \u0441 resolve_normalization_profile_identity."
---

# Episodic summary

## Task

- Title: Синхронизация hash в ChEMBL contract registry

## Outcome

- Обновлен normalization_profile_hash для chembl.assay в configs/base/contract_registry.yaml после изменения canonical Silver seam на assay_description; registry снова совпадает с resolve_normalization_profile_identity.

## Lessons learned

- Replace with durable follow-up if needed
