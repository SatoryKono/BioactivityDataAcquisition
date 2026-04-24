---
Version: 1.0.0
Status: Historical deep schema.
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-24'
---

**⚠️ HISTORICAL CONTENT - ARCHIVED**

This page has been moved to the archive section and is no longer part of the active reference surface.

# ChEMBL Assay Domain Schema (Historical)

**Current Schema**: [ChEMBL assay provider reference](../../../../04-reference/providers/chembl/assay.md)

**Current Config**: `configs/entities/chembl/assay.yaml`

This page is kept as an archived schema note. It reflects a pre-normalization contract and should not be used as the source of truth for current assay fields.

## Migration Notes

- **Status**: This schema page was moved to archive on 2026-04-24 as part of Issue #3092
- **Reason**: Historical deep schema pages create ambiguity with current canonical contracts
- **Replacement**: Use provider reference and entity config for current schema expectations

## Historical Context

Canonical sources:
- [ChEMBL assay provider reference](../../../../04-reference/providers/chembl/assay.md)
- `configs/entities/chembl/assay.yaml`

Current canonical summary:
- Active configs and schema checks use snake_case names.
- Publication and target relationships are represented through the current entity config and provider implementation, not through the legacy dashed names shown in older material.
- Use the provider reference and live config for current assay contract details.
