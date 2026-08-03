---
title: "[P0][testing] TEST-SYS-01: Non-ChEMBL bronze exact-replay fixture promotion"
labels: P0, testing, replay, determinism, quality, golden, coverage
assignees: []
github_issue: 7022
---

## Context

Medallion **exact-replay** confidence is skewed: bronze fixtures are ChEMBL-heavy
(**26/40** files) while VCR is deep for all major providers. Empty
`bronze_fixture_gaps.yaml` means no *registered* gaps, but inventory shows thin
non-ChEMBL bronze relative to HTTP replay depth.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §6 F1  
**Epic:** TEST-SYS-00

## Problem

VCR cassette success ≠ bronze/silver/gold row-level determinism for non-ChEMBL
providers. Families claiming exact replay without representative bronze fixtures
are an architectural replay risk.

## Scope / modules

- `tests/fixtures/bronze/**`
- `configs/base/bronze_fixture_manifest.yaml`
- `configs/base/bronze_fixture_gaps.yaml`
- `configs/quality/fixture_governance_ledger.yaml`
- Architecture gate: `tests/architecture/test_bronze_fixture_replay_baseline.py`
- Priority providers: PubChem, UniProt, publication sources (OpenAlex/Crossref/PubMed/S2) for top entities

## Acceptance Criteria

- [ ] Identify bronze families with exact-replay claim vs thin fixture count (manifest-driven inventory)
- [ ] Promote representative bronze fixtures for at least one critical entity per major non-ChEMBL provider (or register explicit gap with owner + sunset in gaps YAML — not silent absence)
- [ ] Golden Silver/Gold companions where contract requires (ledger-governed)
- [ ] Replay baseline / governance tests green
- [ ] No age-only VCR pruning; no debt-budget growth

## Out of scope

- Mass VCR rewrite
- Live network e2e as substitute for bronze fixtures

## Related

- CHEMBL-014 bronze promotion (ChEMBL-specific)
- NONCHEMBL fixture issues
- TEST-SYS-06 (VCR budget — complementary HTTP surface)
