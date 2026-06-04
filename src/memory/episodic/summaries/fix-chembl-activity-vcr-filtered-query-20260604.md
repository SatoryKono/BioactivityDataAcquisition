---
id: fix-chembl-activity-vcr-filtered-query-20260604
title: Fix ChEMBL activity filtered VCR query drift
task_id: fix-chembl-activity-vcr-filtered-query-20260604
created_at: '2026-06-04T12:31:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/test_activity_extraction_params.py::TestActivityExtractionParams::test_filtered_api_request
summary: Updated the ChEMBL activity extraction-params VCR fixture request URI and
  page_meta.next to include the stricter filtered query parameters used by the current
  adapter contract; refreshed the cassette sidecar sha256. Targeted ChEMBL extraction-params
  replay tests pass. VCR metadata global guards still have unrelated existing drift
  in other cassettes/catalog reachability.
---

# Episodic summary

## Task

- Title: Fix ChEMBL activity filtered VCR query drift

## Outcome

- Updated the ChEMBL activity extraction-params VCR fixture request URI and page_meta.next to include the stricter filtered query parameters used by the current adapter contract; refreshed the cassette sidecar sha256. Targeted ChEMBL extraction-params replay tests pass. VCR metadata global guards still have unrelated existing drift in other cassettes/catalog reachability.

## Lessons learned

- Replace with durable follow-up if needed
