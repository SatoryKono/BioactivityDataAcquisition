---
id: fix-contract-coverage-matrix-drift
title: Fix contract coverage matrix drift and missing contract test paths
task_id: fix-contract-coverage-matrix-drift
created_at: '2026-06-19T15:17:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/contract-coverage-matrix.json
summary: Verified contract coverage matrix drift failures were caused by stale artifact
  rows pointing at pre-repo_backed test paths for publication contract coverage. Current
  reports/quality/contract-coverage-matrix.json and reports/quality/layer-contract-coverage-matrix.json
  use tests/unit/repo_backed/application/pipelines/test_chembl_publication_term_transformer.py
  and tests/unit/repo_backed/domain/normalization/profiles/test_publication_identifier_profiles.py.
  Validated generator check and both layer/gold matrix architecture tests on Linux
  and Windows .venv-win. No runtime source or docs mirror behavior changes required.
---

# Episodic summary

## Task

- Title: Fix contract coverage matrix drift and missing contract test paths

## Outcome

- Verified contract coverage matrix drift failures were caused by stale artifact rows pointing at pre-repo_backed test paths for publication contract coverage. Current reports/quality/contract-coverage-matrix.json and reports/quality/layer-contract-coverage-matrix.json use tests/unit/repo_backed/application/pipelines/test_chembl_publication_term_transformer.py and tests/unit/repo_backed/domain/normalization/profiles/test_publication_identifier_profiles.py. Validated generator check and both layer/gold matrix architecture tests on Linux and Windows .venv-win. No runtime source or docs mirror behavior changes required.

## Lessons learned

- Replace with durable follow-up if needed
