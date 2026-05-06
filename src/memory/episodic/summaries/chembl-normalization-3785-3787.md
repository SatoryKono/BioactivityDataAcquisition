---
id: chembl-normalization-3785-3787
title: 'Implement remaining ChEMBL normalization ownership issues #3785-#3787'
task_id: chembl-normalization-3785-3787
created_at: '2026-05-06T19:58:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Implemented #3785, #3786, and #3787 in runtime code and tests. PublicationTransformer
  now routes through entity_type=publication and leaves publication_type/classification
  semantics domain-authoritative; ChEMBL publication derived classification fields
  are seeded raw and normalized through record-aware profile rules. TargetTransformer
  no longer coerces downgraded to False before domain normalization, preserving null
  semantics. Generic normalize_unit now delegates ChEMBL standard-unit aliases to
  the provider authority in _chembl_units, removing duplicated overlapping mappings
  from rules.py. Verified with targeted ruff, transformer/profile/processor/contract
  tests, snapshot tests, and ChEMBL enum/policy parity tests.'
---

# Episodic summary

## Task

- Title: Implement remaining ChEMBL normalization ownership issues #3785-#3787

## Outcome

- Implemented #3785, #3786, and #3787 in runtime code and tests. PublicationTransformer now routes through entity_type=publication and leaves publication_type/classification semantics domain-authoritative; ChEMBL publication derived classification fields are seeded raw and normalized through record-aware profile rules. TargetTransformer no longer coerces downgraded to False before domain normalization, preserving null semantics. Generic normalize_unit now delegates ChEMBL standard-unit aliases to the provider authority in _chembl_units, removing duplicated overlapping mappings from rules.py. Verified with targeted ruff, transformer/profile/processor/contract tests, snapshot tests, and ChEMBL enum/policy parity tests.

## Lessons learned

- Replace with durable follow-up if needed
