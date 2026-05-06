# [determinism] Enforce one JSON ordering policy for ChEMBL hash canonicalization

## Problem
ChEMBL JSON/list ordering semantics exist in a domain policy module and also appear in entity hash config field_ordering. For example, chembl_json_ordering_policy.py defines order-sensitive and set-like fields across activity, assay, molecule, publication, target, and target_component. Entity configs such as assay, target, and publication also define hash_policy.hash_policy.field_ordering for JSON fields. This duplicates the source of truth for JSON ordering behavior.

## Evidence
- src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py: ChemblJsonOrderingPolicy, CHEMBL_JSON_ORDERING_POLICY, chembl_json_fields, chembl_set_like_json_fields
- configs/entities/chembl/assay.yaml: hash_policy.hash_policy.field_ordering
- configs/entities/chembl/target.yaml: hash_policy.hash_policy.field_ordering
- configs/entities/chembl/publication.yaml: hash_policy.hash_policy.field_ordering
- src/bioetl/domain/normalization/profiles/chembl_assay.py::CHEMBL_ASSAY_PROFILE
- src/bioetl/domain/normalization/profiles/chembl_target.py::CHEMBL_TARGET_PROFILE
- src/bioetl/domain/normalization/profiles/chembl_publication.py::CHEMBL_PUBLICATION_PROFILE

## Root Cause
Duplicate JSON ordering policy surfaces between domain normalization and entity hash configuration.

## Architectural Impact
- Determinism: set-like arrays can hash differently if config and profile disagree
- Idempotency: replay can produce different content hashes for semantically identical JSON
- Gold strict validation: JSON string canonicalization can drift between Silver and Gold
- Composite pipelines: list/set semantics affect join keys, component arrays, author arrays, and derived outputs

## Required Outcome
After the fix:
- one authoritative JSON ordering policy exists for ChEMBL
- hash config and normalization profile cannot disagree on order-sensitive vs set-like fields
- tests cover every JSON-bearing ChEMBL field listed in the policy
- order-sensitive fields preserve provider order
- set-like fields canonicalize deterministically

## Priority
P0 - JSON ordering directly affects canonical serialization and content_hash.

## Size
M - One policy module, entity configs, config validation, and determinism tests.

## Labels
architecture, technical-debt, testing, configs, governance
