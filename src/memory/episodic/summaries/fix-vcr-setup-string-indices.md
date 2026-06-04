---
id: fix-vcr-setup-string-indices
title: Fix VCR setup TypeError string indices
task_id: fix-vcr-setup-string-indices
created_at: '2026-06-04T15:42:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Hardened VCR setup against request-sanitizer TypeError and unresolved Git
  LFS pointer cassettes. build_base_vcr_config now routes header/query filtering through
  a defensive before_record_request sanitizer that no-ops for unexpected request surfaces
  and has unit coverage. Root manual VCR marker runtime now rechecks Git LFS pointers
  immediately before vcr.use_cassette so vcrpy does not parse pointer text as cassette
  YAML. Verified RF013 rebalance VCR suites and VCR helper tests; only malformed cassette
  found by structure scan is the unresolved LFS pointer tests/fixtures/vcr/chembl/test_pipeline_matrix__chembl_publication_similarity.yaml.
---

# Episodic summary

## Task

- Title: Fix VCR setup TypeError string indices

## Outcome

- Hardened VCR setup against request-sanitizer TypeError and unresolved Git LFS pointer cassettes. build_base_vcr_config now routes header/query filtering through a defensive before_record_request sanitizer that no-ops for unexpected request surfaces and has unit coverage. Root manual VCR marker runtime now rechecks Git LFS pointers immediately before vcr.use_cassette so vcrpy does not parse pointer text as cassette YAML. Verified RF013 rebalance VCR suites and VCR helper tests; only malformed cassette found by structure scan is the unresolved LFS pointer tests/fixtures/vcr/chembl/test_pipeline_matrix__chembl_publication_similarity.yaml.

## Lessons learned

- Replace with durable follow-up if needed
