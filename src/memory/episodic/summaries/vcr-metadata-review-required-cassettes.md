---
id: vcr-metadata-review-required-cassettes
title: fix-vcr-metadata-catalog-review-drift
task_id: vcr-metadata-review-required-cassettes
created_at: '2026-05-24T18:09:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/test_activity_extraction_params.py
- tests/integration/chembl/test_assay_extraction_params.py
- tests/integration/chembl/test_publication_extraction_params.py
summary: Confirmed VCR metadata catalog drift came from reachability anchors for pytest-vcr
  auto-named ChEMBL extraction-params cassettes. Current checkout exposes explicit
  VCR_CASSETTE_NAME ownership anchors in the three owning tests, regenerated catalog
  reports metadata_review_required_cassette_count=0, and drift/catalog/VCR policy
  checks pass.
---

# Episodic summary

## Task

- Title: fix-vcr-metadata-catalog-review-drift

## Outcome

- Confirmed VCR metadata catalog drift came from reachability anchors for pytest-vcr auto-named ChEMBL extraction-params cassettes. Current checkout exposes explicit VCR_CASSETTE_NAME ownership anchors in the three owning tests, regenerated catalog reports metadata_review_required_cassette_count=0, and drift/catalog/VCR policy checks pass.

## Lessons learned

- Replace with durable follow-up if needed
