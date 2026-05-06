# [determinism] Consolidate ChEMBL content-hash policy source

## Problem
ChEMBL entity configs expose multiple hash-policy surfaces at the same time: schema.content_hash.include/exclude, contracts.hash_include, and nested hash_policy.hash_policy.include_fields/exclude_fields. The audited configs also contain profile-level normalization/hash-relevant policy such as meta fields and JSON/set-like semantics. This creates more than one apparent source of truth for content_hash behavior.

## Evidence
- configs/entities/chembl/activity.yaml: schema.content_hash.include/exclude (empty), contracts.hash_include (empty), hash_policy.hash_policy.include_fields/exclude_fields (canonical)
- configs/entities/chembl/assay.yaml: schema.content_hash.include/exclude (empty), contracts.hash_include (empty), hash_policy.hash_policy.include_fields/exclude_fields (canonical)
- configs/entities/chembl/target.yaml: schema.content_hash.include/exclude (empty), contracts.hash_include (empty), hash_policy.hash_policy.include_fields/exclude_fields (canonical)
- src/bioetl/domain/normalization/profiles/chembl_activity.py::CHEMBL_ACTIVITY_PROFILE
- src/bioetl/domain/normalization/profiles/chembl_assay.py::CHEMBL_ASSAY_PROFILE
- src/bioetl/domain/normalization/profiles/chembl_target.py::CHEMBL_TARGET_PROFILE
- src/bioetl/infrastructure/config/pipeline_config_api.py

## Root Cause
Design flaw: hash policy is represented in several config/profile surfaces without a single runtime-authoritative contract.

## Architectural Impact
- Determinism / idempotency: replay can produce different content_hash if runtime code reads a different surface
- Reproducibility: effective config fingerprint is ambiguous
- DQ / validation: DQ and hash may disagree on normalized fields included in identity
- Layer boundaries: domain profile should define pure normalization behavior, not compete with infrastructure config hash policy
- Composite pipelines: downstream joins and SCD2 identity can drift if hash semantics change silently

## Required Outcome
After the fix:
- exactly one ChEMBL hash policy source is runtime-authoritative
- deprecated hash surfaces are either removed or validated as empty compatibility shims
- hash include/exclude fields are loaded into one typed config object
- runtime hashing uses that typed config object only
- profile-level normalization rules remain pure canonicalization rules, not independent hash include/exclude policy
- changing hash policy requires explicit contract/hash-policy version note

## Priority
P0 - Hash policy ambiguity directly affects determinism, idempotency, replay, SCD2 identity, and downstream composite behavior.

## Size
L - Multiple ChEMBL configs, config schema, loader behavior, and tests must be updated.

## Labels
architecture, dq, technical-debt, testing, configs, governance
