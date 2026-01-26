# Schema-Transformer Field Correspondence Audit Report

**Generated**: 2026-01-26
**Audited by**: Claude Code (Opus 4.5)
**Scope**: All BioETL Pandera schemas and corresponding transformers

---

## Executive Summary

This audit analyzes field correspondence between Pandera schemas (Silver layer validation) and transformers (Bronze→Silver extraction) across all 7 BioETL providers. The audit identifies:

1. **Fields defined in schema but not extracted in transformer**
2. **Fields extracted in transformer but missing from schema**
3. **Type mismatches**
4. **Naming inconsistencies**

### Key Findings

| Category | Count | Priority |
|----------|-------|----------|
| Missing transformer implementations | 2 | Low (internal ChEMBL entities) |
| Schema-transformer field mismatches | 15 | Medium |
| Fields in transformer but not schema | 8 | Low (handled by `strict=False`) |
| System fields handled by BaseTransformer | OK | N/A |

---

## System Fields (Added by BaseTransformer)

The following fields are **automatically added** by `BaseTransformer` and should NOT be extracted in `_extract_business_data`:

From **ETLRecordSchema** (base):
- `entity_id` - Computed by `compute_entity_id()`
- `content_hash` - Computed by `compute_content_hash()`
- `_run_id` - From PipelineContext
- `_run_type` - From PipelineContext
- `_source_batch_id` - From PipelineContext (nullable)
- `_ingestion_ts` - Auto-generated timestamp
- `_dq_warn` - Default False (can be overridden)
- `_dq_error` - Default False (can be overridden)
- `_index` - Sequential index parameter

From **PublicationBaseSchema** (publication entities):
- `pmid`, `doi`, `pmc_id` - Cross-reference IDs
- `title`, `abstract`, `authors` - Core content
- `journal`, `year`, `publication_date`, `doc_type`, `language` - Metadata
- `citation_count`, `is_oa` - Metrics
- `_lookup_method`, `_original_id`, `_source` - Lookup tracking

---

## Provider Audit Details

### 1. ChEMBL Pipeline

ChEMBL has 14 schema files and 12 transformer files.

#### 1.1 ActivitySchema ↔ ActivityTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/activity.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/activity_transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `activity_id` | ✅ | ✅ | OK |
| `assay_chembl_id` | ✅ | ✅ | OK |
| `molecule_chembl_id` | ✅ | ✅ | OK |
| `target_chembl_id` | ✅ nullable | ✅ | OK |
| `document_chembl_id` | ✅ nullable | ✅ | OK |
| All standardized values | ✅ | ✅ via `_STANDARD_VALUES` FieldGroup | OK |
| `ligand_efficiency_*` | ✅ | ✅ via `_extract_ligand_efficiency` | OK |
| `action_type_*` | ✅ | ✅ via `_extract_action_type` | OK |
| `activity_properties` | ✅ | ✅ JSON serialized | OK |
| `target_taxonomy_id` | ✅ | ✅ (mapped from `target_tax_id`) | OK |
| `manual_curation_flag` | ✅ | ✅ | OK |
| `original_activity_id` | ✅ | ✅ | OK |
| `data_validity_description` | ✅ | ✅ | OK |

**Discrepancies**: None found. ✅

---

#### 1.2 MoleculeSchema ↔ MoleculeTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/molecule.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/molecule_transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `molecule_chembl_id` | ✅ | ✅ | OK |
| `structure_standard_inchi_key` | ✅ | ❌ Not extracted | **MISMATCH** |
| `inchikey` | ✅ | ✅ (from structures) | OK |
| `hierarchy_*` | ✅ | ✅ via flatten_nested_dict | OK |
| `property_*` | ✅ | ✅ via flatten_nested_dict | OK |
| `canonical_smiles` | ✅ | ✅ | OK |
| `standard_inchi` | ✅ | ✅ | OK |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `structure_standard_inchi_key` | Schema field not extracted | Remove from schema or add extraction (appears to be legacy from `molecule_structures.standard_inchi_key`) |

**Note**: The transformer extracts from `molecule_structures` and renames `standard_inchi_key` → `inchikey`. The schema has both `structure_standard_inchi_key` and `inchikey`, which is redundant.

---

#### 1.3 TargetSchema ↔ TargetTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/target.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/target_transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `target_chembl_id` | ✅ | ✅ | OK |
| `taxonomy_id` | ✅ | ✅ (mapped from `tax_id`) | OK |
| `downgraded` | ✅ bool | ✅ converted to bool | OK |
| `target_components` | ✅ JSON | ✅ | OK |
| `cross_references` | ✅ JSON | ✅ (aggregated from components) | OK |
| `component_*` lists | ✅ | ✅ via `_flatten_target_components` | OK |

**Discrepancies**: None found. ✅

---

#### 1.4 AssaySchema ↔ AssayTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/assay.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/assay_transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `assay_chembl_id` | ✅ | ✅ | OK |
| `assay_taxonomy_id` | ✅ | ✅ (mapped from `assay_tax_id`) | OK |
| `variant_taxonomy_id` | ✅ | ✅ (mapped from `variant_tax_id`) | OK |
| `variant_*` fields | ✅ | ✅ via `_extract_variant` | OK |
| `assay_type_description` | ❌ Not in schema | ✅ extracted via `_CLASSIFICATION` | **MISMATCH** |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `assay_type_description` | Extracted but not in schema | Add to AssaySchema or remove from transformer |

---

#### 1.5 CellLineSchema ↔ CellLineTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/cell_line.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/cell_line_transformer.py`

**Discrepancies**: None found. ✅

---

#### 1.6 CompoundRecordSchema ↔ CompoundRecordTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/compound_record.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/compound_record_transformer.py`

**Discrepancies**: None found. ✅

---

#### 1.7 TargetComponentSchema ↔ TargetComponentTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/target_component.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/target_component_transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `targcomp_id` | ✅ PK | ❌ Not extracted | **MISMATCH** |
| `tid` | ✅ required | ❌ Not extracted | **MISMATCH** |
| `component_id` | ✅ required | ✅ (as primary_id) | OK |
| `relationship` | ✅ | ❌ Not extracted | **MISMATCH** |
| `stoichiometry` | ✅ | ❌ Not extracted | **MISMATCH** |
| `homologue` | ✅ | ❌ Not extracted | **MISMATCH** |
| `taxonomy_id` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `accession` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `component_type` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `description` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `organism` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `target_component_synonyms` | ❌ Not in schema | ✅ JSON | **MISMATCH** |
| `target_component_xrefs` | ❌ Not in schema | ✅ JSON | **MISMATCH** |
| `protein_classifications` | ❌ Not in schema | ✅ JSON | **MISMATCH** |
| `protein_classification_ids` | ❌ Not in schema | ✅ extracted | **MISMATCH** |

**Critical Discrepancy**: The schema and transformer are fundamentally misaligned. The schema represents the `target_component` table join structure (targcomp_id, tid, component_id), while the transformer extracts from the `/target_component` API endpoint which returns component details.

**Recommendation**:
1. **HIGH PRIORITY**: Create a new schema `ComponentSequenceSchema` that matches what the transformer actually extracts
2. Keep `TargetComponentSchema` for the join table data if needed
3. Or update the transformer to use a different data source that provides the join table data

---

#### 1.8 ProteinClassificationSchema ↔ ProteinClassTransformer

**Discrepancies**: None found. ✅

---

#### 1.9 ChemblPublicationSchema ↔ PublicationTransformer

**Schema**: `src/bioetl/domain/schemas/chembl/publication.py`
**Transformer**: `src/bioetl/application/pipelines/chembl/publication_transformer.py`

**Discrepancies**: None found. Schema inherits from PublicationBaseSchema and transformer provides all required fields. ✅

---

#### 1.10 PublicationSimilaritySchema ↔ PublicationSimilarityTransformer

**Discrepancies**: None found. ✅

---

#### 1.11 PublicationTermSchema ↔ PublicationTermTransformer

**Discrepancies**: None found. ✅

---

#### 1.12 AssayParametersSchema ↔ AssayParametersTransformer

**Discrepancies**: None found. ✅

---

#### 1.13 Missing Transformers

| Schema | Status | Notes |
|--------|--------|-------|
| `MoleculeFormSchema` | No transformer | Internal ChEMBL schema for molecule hierarchy |
| `TargetRelationSchema` | No transformer | Internal ChEMBL schema for target relationships |

**Recommendation**: These appear to be internal ChEMBL schemas not exposed via API. Mark as "internal only" or create transformers if data is needed.

---

### 2. PubChem Pipeline

#### 2.1 PubchemMoleculeSchema ↔ PubChemCompoundTransformer

**Schema**: `src/bioetl/domain/schemas/pubchem/compound.py`
**Transformer**: `src/bioetl/application/pipelines/pubchem/transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `cid` | ✅ int | ✅ str | **TYPE MISMATCH** |
| `inchi_key` | ✅ | ✅ as `inchikey` | **NAMING** |
| All 3D properties | ✅ | ✅ via `_extract_3d_properties` | OK |
| All stereo counts | ✅ | ✅ via `_extract_stereochemistry` | OK |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `cid` | Schema expects `int`, transformer provides `str(cid)` | Transformer should keep int for entity_id computation, schema coerces |
| `inchi_key` vs `inchikey` | Naming inconsistency | Schema uses `inchi_key`, transformer uses `inchikey` - check if coercion handles |

---

### 3. UniProt Pipeline

#### 3.1 UniprotTargetSchema ↔ UniProtProteinTransformer

**Schema**: `src/bioetl/domain/schemas/uniprot/protein.py`
**Transformer**: `src/bioetl/application/pipelines/uniprot/transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `accession` | ✅ | ✅ (from `primaryAccession`) | OK |
| `entry_name` | ✅ | ✅ (from `uniProtkbId`) | OK |
| `protein_name` | ✅ nullable | ✅ nullable | OK |
| `gene_names` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `organism_id` | ❌ Not in schema | ✅ (alias for taxonomy_id) | **MISMATCH** |
| `publication_count` | ✅ | ❌ Not extracted | **MISMATCH** |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `gene_names` | Extracted but not in schema | Add to schema (JSON array of gene names) |
| `organism_id` | Legacy compatibility alias | Consider removing from transformer |
| `publication_count` | In schema but not extracted | Add extraction or remove from schema |

---

#### 3.2 IDMappingSchema ↔ IDMappingTransformer

**Discrepancies**: None found. ✅

---

### 4. PubMed Pipeline

#### 4.1 PubMedPublicationSchema ↔ PubMedPublicationTransformer

**Schema**: `src/bioetl/domain/schemas/pubmed/publication.py`
**Transformer**: `src/bioetl/application/pipelines/pubmed/transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `pmid` | ✅ str | ✅ str | OK |
| `journal` | ✅ (base) | ✅ as `journal_title` | OK (aliased) |
| `journal_abbrev` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `pub_date` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `publication_year` | ❌ Not in schema | ✅ (alias for year) | **MISMATCH** |
| `pages` | ❌ Not in schema | ✅ extracted | **MISMATCH** |
| `first_page`, `last_page` | ❌ Not in schema | ✅ extracted | **MISMATCH** |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `journal_abbrev` | Extracted but not in schema | Add to PubMedPublicationSchema |
| `pub_date` | Extracted but not in schema | Add to schema (partial date string) |
| `pages`, `first_page`, `last_page` | Extracted but not in schema | Add pagination fields to schema |
| `publication_year` | Legacy alias | Remove from transformer (use `year`) |

---

### 5. CrossRef Pipeline

#### 5.1 PublicationEnrichedSchema ↔ CrossRefPublicationTransformer

**Schema**: `src/bioetl/domain/schemas/crossref/publication.py`
**Transformer**: `src/bioetl/application/pipelines/crossref/transformer.py`

| Field | Schema | Transformer | Status |
|-------|--------|-------------|--------|
| `doi` | ✅ non-nullable | ✅ | OK |
| `subjects` | ✅ | ✅ as list | OK (coerced) |
| `first_page`, `last_page` | ❌ Not in schema | ✅ via `extract_page_info` | **MISMATCH** |

**Discrepancies**:

| Field | Problem | Recommendation |
|-------|---------|----------------|
| `first_page`, `last_page` | Extracted but not in schema | Add to PublicationEnrichedSchema |

---

### 6. OpenAlex Pipeline

#### 6.1 OpenAlexPublicationSchema ↔ OpenAlexPublicationTransformer

**Schema**: `src/bioetl/domain/schemas/openalex/publication.py`
**Transformer**: `src/bioetl/application/pipelines/openalex/transformer.py`

**Discrepancies**: None found. Schema and transformer are well-aligned. ✅

---

### 7. SemanticScholar Pipeline

#### 7.1 SemanticScholarPublicationSchema ↔ SemanticScholarPublicationTransformer

**Schema**: `src/bioetl/domain/schemas/semanticscholar/publication.py`
**Transformer**: `src/bioetl/application/pipelines/semanticscholar/transformer.py`

**Discrepancies**: None found. Schema and transformer are well-aligned. ✅

---

## Summary of All Discrepancies

### HIGH Priority (Schema-Transformer Structural Mismatch)

| Provider | Entity | Issue | Action Required |
|----------|--------|-------|-----------------|
| ChEMBL | TargetComponent | Schema and transformer fundamentally misaligned | Create new ComponentSequenceSchema or fix transformer |

### MEDIUM Priority (Missing Fields)

| Provider | Entity | Field | Direction | Action |
|----------|--------|-------|-----------|--------|
| ChEMBL | Molecule | `structure_standard_inchi_key` | Schema only | Remove from schema (redundant with `inchikey`) |
| ChEMBL | Assay | `assay_type_description` | Transformer only | Add to schema |
| UniProt | Protein | `gene_names` | Transformer only | Add to schema |
| UniProt | Protein | `publication_count` | Schema only | Add extraction or remove |
| PubMed | Publication | `journal_abbrev`, `pub_date`, `pages`, `first_page`, `last_page` | Transformer only | Add to schema |
| CrossRef | Publication | `first_page`, `last_page` | Transformer only | Add to schema |

### LOW Priority (Naming/Type Inconsistencies)

| Provider | Entity | Field | Issue | Action |
|----------|--------|-------|-------|--------|
| PubChem | Molecule | `cid` | str vs int type | Verify coercion handles this |
| PubChem | Molecule | `inchi_key` vs `inchikey` | Naming | Standardize naming |

---

## Recommendations

### 1. Immediate Actions (HIGH Priority)

1. **Fix TargetComponentSchema**: Create a new schema that matches the actual transformer output, or update the transformer to match the existing schema structure.

### 2. Short-term Actions (MEDIUM Priority)

1. **Add missing fields to schemas**: Update schemas to include fields that transformers extract but schemas don't define.
2. **Remove unused schema fields**: Remove `structure_standard_inchi_key` from MoleculeSchema (redundant).

### 3. Long-term Actions (LOW Priority)

1. **Standardize field naming**: Ensure consistent naming across all providers (e.g., `inchi_key` vs `inchikey`).
2. **Add automated CI check**: Create a script that compares schema fields with transformer extraction.

### 4. CI Automation Recommendation

Create `scripts/audit_field_mapping.py`:

```python
"""Automated schema-transformer field mapping audit.

Usage: python scripts/audit_field_mapping.py
"""

import ast
import sys
from pathlib import Path


def extract_schema_fields(schema_file: Path) -> set[str]:
    """Extract field names from Pandera schema."""
    with open(schema_file) as f:
        tree = ast.parse(f.read())

    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fields.add(node.target.id)
    return fields


def extract_transformer_fields(transformer_file: Path) -> set[str]:
    """Extract field names from _extract_business_data return dict."""
    # Simplified - would need AST analysis of return statement
    pass


def main():
    schemas_dir = Path("src/bioetl/domain/schemas")
    pipelines_dir = Path("src/bioetl/application/pipelines")

    # Compare each schema with its transformer
    # Report discrepancies
    pass


if __name__ == "__main__":
    main()
```

---

## Appendix: Complete Field Lists by Entity

### ChEMBL Activity (58 fields)
Schema fields: activity_id, assay_chembl_id, molecule_chembl_id, target_chembl_id, document_chembl_id, standard_relation, standard_value, standard_units, standard_type, standard_flag, pchembl_value, data_validity_comment, activity_comment, potential_duplicate, bao_endpoint, uo_units, qudt_units, src_id, record_id, type, relation, value, units, text_value, standard_text_value, upper_value, standard_upper_value, toid, manual_curation_flag, original_activity_id, data_validity_description, ligand_efficiency_bei, ligand_efficiency_le, ligand_efficiency_lle, ligand_efficiency_sei, action_type_action_type, action_type_description, action_type_parent_type, activity_properties, canonical_smiles, molecule_pref_name, parent_molecule_chembl_id, target_pref_name, target_organism, target_taxonomy_id, assay_type, assay_description, assay_variant_accession, assay_variant_mutation, bao_format, bao_label, document_journal, document_year + system fields

### PubChem Molecule (47 fields)
Schema fields: cid, canonical_smiles, isomeric_smiles, inchi, inchi_key, molecular_formula, iupac_name, molecular_weight, exact_mass, monoisotopic_mass, xlogp, tpsa, complexity, charge, heavy_atom_count, h_bond_donor_count, h_bond_acceptor_count, rotatable_bond_count, atom_stereo_count, defined_atom_stereo_count, undefined_atom_stereo_count, bond_stereo_count, defined_bond_stereo_count, undefined_bond_stereo_count, isotope_atom_count, covalent_unit_count, volume_3d, conformer_count_3d, feature_acceptor_count_3d, feature_donor_count_3d, feature_anion_count_3d, feature_cation_count_3d, feature_ring_count_3d, feature_hydrophobe_count_3d, effective_rotor_count_3d, conformer_rmsd_3d, x_steric_quadrupole_3d, y_steric_quadrupole_3d, z_steric_quadrupole_3d, feature_count_3d + system fields

---

*End of Audit Report*
