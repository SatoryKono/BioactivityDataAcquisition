---
Version: 1.0.0
Status: Historical deep spec.
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ChEMBL Publication Term Pipeline Deep Spec

This page is preserved for historical analysis only. It describes an older contract shape and legacy loading-strategy wording.

Canonical sources:
- [ChEMBL publication provider reference](../../providers/chembl/publication.md)
- `configs/entities/chembl/publication_term.yaml`

Current canonical summary:
- The active config surface uses snake_case keys such as `loading_strategy`.
- Publication identifiers and alias mappings are defined in the entity config and current provider pipeline implementation.
- Use the entity config and provider reference for current behavior; do not copy field names or loading examples from this legacy page.
