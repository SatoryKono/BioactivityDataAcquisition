---
id: chembl-winerror-10055
title: Debug ChEMBL WinError 10055 integration failures
task_id: chembl-winerror-10055
created_at: '2026-06-18T07:32:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/test_assay_extraction_params.py
summary: Marked the ChEMBL extraction-params async VCR tests with pytest.mark.asyncio(loop_scope="module")
  to avoid Windows socket buffer exhaustion from repeated event-loop creation; targeted
  extraction-params suites passed.
---

# Episodic summary

## Task

- Title: Debug ChEMBL WinError 10055 integration failures

## Outcome

- Marked the ChEMBL extraction-params async VCR tests with pytest.mark.asyncio(loop_scope="module") to avoid Windows socket buffer exhaustion from repeated event-loop creation; targeted extraction-params suites passed.

## Lessons learned

- Replace with durable follow-up if needed
