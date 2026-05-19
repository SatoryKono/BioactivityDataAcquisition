---
id: implement-chembl-assay-gold-filtering
title: Implement chembl_assay gold filtering expansion
task_id: implement-chembl-assay-gold-filtering
created_at: '2026-05-19T11:44:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/assay.yaml
- tests/integration/config/test_dq_config_loading.py
- tests/integration/config/test_chembl_enum_parity.py
- tests/contract/test_chembl_enum_normalization_policy.py
- tests/integration/config/test_chembl_policy_surface_parity.py
- docs/04-reference/pipelines/chembl-assay.md
- docs/04-reference/providers/chembl/assay.md
summary: Expanded chembl_assay gold filtering with operator-based rules for assay_test_type,
  assay_strain, and bao_format; aligned config/parity helpers and chembl assay reference
  docs; validated with targeted config/contract tests and chembl assay E2E.
---

# Episodic summary

## Task

- Title: Implement chembl_assay gold filtering expansion

## Outcome

- Expanded chembl_assay gold filtering with operator-based rules for assay_test_type, assay_strain, and bao_format; aligned config/parity helpers and chembl assay reference docs; validated with targeted config/contract tests and chembl assay E2E.

## Lessons learned

- Replace with durable follow-up if needed
