---
id: chembl-adapter-fetch-timeout
title: Fix ChEMBL adapter fetch activities timeout
task_id: chembl-adapter-fetch-timeout
created_at: '2026-06-04T12:15:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed flaky timeout in tests/integration/adapters/test_chembl.py::TestChemblAdapter::test_fetch_activities
  by replacing the live UnifiedHTTPClient fixture with a deterministic replay HTTP
  seam for adapter-level ChEMBL integration tests. Removed VCR markers from those
  replay-backed tests and updated docstrings. Validation passed for ruff, WSL single
  test, WSL full test_chembl.py, and Windows .venv-win single test.
---

# Episodic summary

## Task

- Title: Fix ChEMBL adapter fetch activities timeout

## Outcome

- Fixed flaky timeout in tests/integration/adapters/test_chembl.py::TestChemblAdapter::test_fetch_activities by replacing the live UnifiedHTTPClient fixture with a deterministic replay HTTP seam for adapter-level ChEMBL integration tests. Removed VCR markers from those replay-backed tests and updated docstrings. Validation passed for ruff, WSL single test, WSL full test_chembl.py, and Windows .venv-win single test.

## Lessons learned

- Replace with durable follow-up if needed
