---
id: vcr-metadata-catalog-drift-fix
title: Fix VCR metadata catalog drift
task_id: vcr-metadata-catalog-drift-fix
created_at: '2026-06-02T09:16:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/vcr-metadata-catalog.json
- tests/architecture/test_vcr_metadata_catalog_drift.py
- scripts/engineering/qa/report_vcr_metadata_catalog.py
summary: Confirmed VCR metadata catalog is up to date; direct pytest passes; run_pytest.sh
  is blocked by pretest catalog-check governance failure active script count 372 >
  368
---

# Episodic summary

## Task

- Title: Fix VCR metadata catalog drift

## Outcome

- Confirmed VCR metadata catalog is up to date; direct pytest passes; run_pytest.sh is blocked by pretest catalog-check governance failure active script count 372 > 368

## Lessons learned

- Replace with durable follow-up if needed
