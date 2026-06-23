---
id: fix-semantic-anchor-parity-publication-id
title: Fix semantic anchor parity for chembl publication identifier
task_id: fix-semantic-anchor-parity-publication-id
created_at: '2026-06-23T06:56:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/publication.yaml
summary: 'Fixed chembl publication semantic anchor parity by requiring publication_id
  in silver and gold filter required_fields. Validation passed: semantic anchor parity
  check, targeted pytest for tests/integration/config/test_semantic_anchor_parity.py,
  required-fields schema check, and config validation.'
---

# Episodic summary

## Task

- Title: Fix semantic anchor parity for chembl publication identifier

## Outcome

- Fixed chembl publication semantic anchor parity by requiring publication_id in silver and gold filter required_fields. Validation passed: semantic anchor parity check, targeted pytest for tests/integration/config/test_semantic_anchor_parity.py, required-fields schema check, and config validation.

## Lessons learned

- Replace with durable follow-up if needed
