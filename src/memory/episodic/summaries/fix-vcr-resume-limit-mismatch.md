---
id: fix-vcr-resume-limit-mismatch
title: Fix ChEMBL resume VCR limit mismatch
task_id: fix-vcr-resume-limit-mismatch
created_at: '2026-05-18T18:41:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_chembl_activity_e2e.py
summary: Aligned tests/e2e/test_chembl_activity_e2e.py resume checkpoint scenario
  with existing VCR cassette by changing the local resume limit from 5 to 3. Validation
  confirmed the original CannotOverwriteExistingCassetteException no longer occurs;
  the test now proceeds to an unrelated pre-existing Silver table path assertion failure
  in assert_silver_table_has_records.
---

# Episodic summary

## Task

- Title: Fix ChEMBL resume VCR limit mismatch

## Outcome

- Aligned tests/e2e/test_chembl_activity_e2e.py resume checkpoint scenario with existing VCR cassette by changing the local resume limit from 5 to 3. Validation confirmed the original CannotOverwriteExistingCassetteException no longer occurs; the test now proceeds to an unrelated pre-existing Silver table path assertion failure in assert_silver_table_has_records.

## Lessons learned

- Replace with durable follow-up if needed
