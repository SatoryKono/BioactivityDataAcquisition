# ChEMBL Publication Similarity Pipeline Deep Spec

Status: Historical deep spec.

This document is kept only as archived design context. It predates the normalized snake_case contract and should not be used as active implementation guidance.

Canonical sources:
- [ChEMBL publication provider reference](../../providers/chembl/publication.md)
- `configs/entities/chembl/publication_similarity.yaml`

Current canonical summary:
- Current config keys use snake_case, including `loading_strategy`.
- Canonical publication identifiers and downstream field mappings are owned by the live entity config and application pipeline code.
- Treat this file as historical evidence, not as the current publication similarity contract.
