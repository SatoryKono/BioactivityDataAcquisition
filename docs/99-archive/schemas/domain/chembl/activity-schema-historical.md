______________________________________________________________________

Version: 1.0.0
Status: Historical deep schema.
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-24'

______________________________________________________________________

**⚠️ HISTORICAL CONTENT - ARCHIVED**

This page has been moved to the archive section and is no longer part of the active reference surface.

# ChEMBL Activity Domain Schema (Historical)

**Current Schema**: [ChEMBL activity provider reference](../../../../04-reference/providers/chembl/activity.md)

**Current Config**: `configs/entities/chembl/activity.yaml`

This page is retained as a historical schema artifact. It predates the current normalized field contract and contains legacy dashed publication identifiers.

## Migration Notes

- **Status**: This schema page was moved to archive on 2026-04-24 as part of Issue #3092
- **Reason**: Historical deep schema pages create ambiguity with current canonical contracts
- **Replacement**: Use provider reference and entity config for current schema expectations

## Historical Context

Canonical sources:

- [ChEMBL activity provider reference](../../../../04-reference/providers/chembl/activity.md)
- `configs/entities/chembl/activity.yaml`

Current canonical summary:

- The live contract uses snake_case field names and config-driven alias resolution.
- Publication linkage and related identifiers are defined in the entity config and current transformer implementation.
- For current schema expectations, use the provider reference, current entity config, and runtime validation artifacts instead of this archived schema page.
