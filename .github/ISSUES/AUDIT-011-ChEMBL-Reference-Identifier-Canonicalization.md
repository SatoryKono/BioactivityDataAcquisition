# [dq] Add shared ChEMBL reference-identifier canonicalization policy

## Problem
Ontology-backed identifiers have a shared policy registry for BAO, UO, BTO, CALOHA, EFO, CLO, UBERON, and Cellosaurus. Other ChEMBL reference identifiers such as taxonomy IDs, CHEMBL IDs, accessions, DOI, PMID, PMCID, and MeSH IDs are handled through local profile/config patterns and field-specific normalizers. They are not governed by the same explicit shared reference-identifier policy surface.

## Evidence
- configs/vocab/chembl_ontology.yaml: ontology families: bao, uo, bto, caloha, efo, clo, uberon, cellosaurus
- configs/entities/chembl/target.yaml: taxonomy_id local range validation
- configs/entities/chembl/cell_line.yaml: cell_source_taxonomy_id, cellosaurus_id, clo_id, efo_id
- src/bioetl/domain/normalization/profiles/chembl_target.py: _INT_FIELDS = {"taxonomy_id"}
- src/bioetl/domain/normalization/profiles/chembl_cell_line.py
- src/bioetl/domain/normalization/profiles/chembl_target_component.py: accession, taxonomy_id
- src/bioetl/domain/normalization/profiles/chembl_publication.py: _DOI_FIELDS, _PMID_FIELDS, _PMC_ID_FIELDS
- src/bioetl/domain/normalization/profiles/chembl_publication_term.py: mesh_id

## Root Cause
Reference identifiers that are not ontology families lack a shared canonicalization/governance layer.

## Architectural Impact
- DQ / validation: reference-ID validation is entity-local and can drift
- Composite pipelines: join keys and identifiers can canonicalize differently across pipelines
- Determinism / hash: casing or format differences can affect content hash
- Medallion: Silver normalization of identifiers is not uniformly governed

## Required Outcome
After the fix:
- ChEMBL reference identifiers are classified separately from strict enums and ontology identifiers
- shared canonicalization exists for: CHEMBL IDs, NCBI taxonomy IDs, UniProt-like accessions, DOI, PMID, PMCID, MeSH IDs
- domain reference-ID normalization remains pure
- configs/DQ reference the shared policy instead of ad-hoc local patterns where applicable

## Priority
P1 - This removes cross-pipeline identifier drift risk, especially for composite joins and hash identity.

## Size
L - Requires new shared policy, multiple profiles, configs, and tests.

## Labels
dq, refactor, testing, configs, governance
