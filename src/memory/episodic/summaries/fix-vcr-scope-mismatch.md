---
id: fix-vcr-scope-mismatch
title: Fix VCR fixture scope mismatch
task_id: fix-vcr-scope-mismatch
created_at: '2026-05-21T09:31:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_pubmed_publication_e2e.py
summary: Changed E2E vcr_config fixtures that depend on per-test vcr_cassette_dir
  from module scope to function scope, eliminating pytest ScopeMismatch during VCR
  setup.
---

# Episodic summary

## Task

- Title: Fix VCR fixture scope mismatch

## Outcome

- Changed E2E vcr_config fixtures that depend on per-test vcr_cassette_dir from module scope to function scope, eliminating pytest ScopeMismatch during VCR setup.

## Lessons learned

- Replace with durable follow-up if needed
