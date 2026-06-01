---
id: chembl-uniprot-multiprovider-vcr-drift-20260601
title: Fix multi-provider Chembl/UniProt VCR drift after target classification refactor
task_id: chembl-uniprot-multiprovider-vcr-drift-20260601
created_at: '2026-06-01T15:24:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/conftest.py
- tests/fixtures/vcr/multi_provider/test_chembl_and_uniprot_sequential_run.yaml
- tests/fixtures/vcr/multi_provider/test_chembl_and_uniprot_sequential_run_meta.yaml
summary: Refreshed the multi-provider cassette for test_chembl_and_uniprot_sequential_run
  after chembl_target began resolving target_component and protein_classification
  lookups; also allowed e2e VCR tests in recording mode to retain cassette-backed
  input snapshot refs and rewrote the managed metadata sidecar.
---

# Episodic summary

## Task

- Title: Fix multi-provider Chembl/UniProt VCR drift after target classification refactor

## Outcome

- Refreshed the multi-provider cassette for test_chembl_and_uniprot_sequential_run after chembl_target began resolving target_component and protein_classification lookups; also allowed e2e VCR tests in recording mode to retain cassette-backed input snapshot refs and rewrote the managed metadata sidecar.

## Lessons learned

- Replace with durable follow-up if needed
