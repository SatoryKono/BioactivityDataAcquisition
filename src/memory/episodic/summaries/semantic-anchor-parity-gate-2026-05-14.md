---
id: semantic-anchor-parity-gate-2026-05-14
title: Implement semantic anchor DQ Gold parity gate
task_id: semantic-anchor-parity-gate-2026-05-14
created_at: '2026-05-14T16:37:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/check_semantic_anchor_parity.py
summary: Added semantic anchor parity QA gate for doi, pmid, title, assay_id, molecule_id,
  and inchi_key across entity DQ, Gold contracts, and composite join/output-key surfaces.
  Added routed scripts.engineering.qa command, integration tests, and canonical field
  registry documentation. Validation passed for direct/routed parity checks, ruff,
  py_compile, semantic anchor pytest, semantic field unification pytest, and import
  boundary scan; full docs drift check is blocked by an existing OSError on an unrelated
  docs report path, changed doc was checked directly for forbidden patterns.
---

# Episodic summary

## Task

- Title: Implement semantic anchor DQ Gold parity gate

## Outcome

- Added semantic anchor parity QA gate for doi, pmid, title, assay_id, molecule_id, and inchi_key across entity DQ, Gold contracts, and composite join/output-key surfaces. Added routed scripts.engineering.qa command, integration tests, and canonical field registry documentation. Validation passed for direct/routed parity checks, ruff, py_compile, semantic anchor pytest, semantic field unification pytest, and import boundary scan; full docs drift check is blocked by an existing OSError on an unrelated docs report path, changed doc was checked directly for forbidden patterns.

## Lessons learned

- Replace with durable follow-up if needed
