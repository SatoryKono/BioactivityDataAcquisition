______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# ChEMBL Normalization Deep Dive

**Issue:** #6559
**Entry SSOT:** [chembl-normalization-overview.md](chembl-normalization-overview.md)

## Scope

Deep operator/developer guide for ChEMBL family normalization across activity,
molecule, target, assay, and related entities.

## Authority stack

| Layer | Location |
| --- | --- |
| Overview | this family + overview page |
| Enums | `configs/enums/chembl.yaml` |
| Controlled vocab | `configs/vocab/chembl_controlled.yaml` |
| Ontology policy | `configs/vocab/chembl_ontology.yaml` |
| Profiles | `src/bioetl/domain/normalization/profiles/` |
| Generated matrix | `docs/reports/generated/pipeline_normalization_field_matrix/` |
| Pipeline specs | `docs/04-reference/pipelines/chembl/` |

## Entity focus

### Activity

- Standard type / value / units canonicalization
- Relation operators and null/zero handling
- Assay linkage identifiers
- DQ: unit and type enums from SSOT, not free text

### Molecule

- Structure/identifier fields via profile
- Name/synonym handling without dual SSOT
- Chirality / molecule type only through governed surfaces

### Target

- Protein classification and organism fields
- Cross-references as structured fields with vocab checks
- Component JSON canonicalization before hashing

### Assay / assay parameters

- Parameter name/value normalization through profile-owned rules
- Optional unit ontology companion when configured

## Identity and hashing

- Business keys + `content_hash` after normalization
- Do not put `run_id` into hash identity
- Changing canonicalization **changes hashes** — treat as breaking

## Testing

- Bronze fixtures for covered pipelines
- Enum drift tests (SSOT subset checks)
- VCR for HTTP extract paths

## Related diagrams

- `docs/02-architecture/diagrams/providers/chembl/*.mmd`
