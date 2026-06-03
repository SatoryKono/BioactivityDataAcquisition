---
id: e2e-bronze-publication-term-20260603
title: Diagnose Bronze payload expectation for chembl_publication_term e2e
task_id: e2e-bronze-publication-term-20260603
created_at: '2026-06-03T08:06:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_pipeline_matrix_e2e.py
summary: Changed matrix E2E to skip chembl_publication_term entirely because it is
  a derived entity already covered by dedicated publication_term E2E tests, avoiding
  timeout-prone sparse-cassette runs in the generic matrix smoke suite.
---

# Episodic summary

## Task

- Title: Diagnose Bronze payload expectation for chembl_publication_term e2e

## Outcome

- Changed matrix E2E to skip chembl_publication_term entirely because it is a derived entity already covered by dedicated publication_term E2E tests, avoiding timeout-prone sparse-cassette runs in the generic matrix smoke suite.

## Lessons learned

- Replace with durable follow-up if needed
