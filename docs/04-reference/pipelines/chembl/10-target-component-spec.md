# ChEMBL Target Component Pipeline Deep Spec

Status: Historical deep spec.

This document is retained as a legacy implementation note. It describes pre-normalization field names and should not be treated as the current contract.

Canonical sources:
- [ChEMBL target component provider reference](../../providers/chembl/target-component.md)
- [`configs/entities/chembl/target_component.yaml`](../../../../configs/entities/chembl/target_component.yaml)

Current canonical summary:
- Active configs and reference examples use snake_case names.
- Component relationships, identifiers, and alias handling are defined in the current entity config and provider transformer logic.
- Use the provider reference plus the live config as the source of truth for target component fields and loading behavior.
