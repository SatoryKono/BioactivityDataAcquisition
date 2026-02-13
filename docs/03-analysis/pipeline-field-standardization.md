# Pipeline Field Standardization Analysis

*Date: 2026-02-13 | Pipelines: activity, assay, target, molecule*

---

## 1. Overview

This document analyzes field naming across four ChEMBL pipelines (`activity`, `assay`, `target`, `molecule`),
identifies inconsistencies, and proposes unified naming conventions for Silver layer.

**Sources analyzed:**
- Pandera schemas: `src/bioetl/domain/schemas/chembl/{entity}.py`
- Transformers: `src/bioetl/application/pipelines/chembl/{entity}_transformer.py`
- Domain entities: `src/bioetl/domain/entities/`
- DTOs: `src/bioetl/domain/entities/chembl.py`

---

## 2. Field Inventory per Pipeline

### 2.1 Activity Pipeline (62 fields)

| # | Silver Field Name | Type | Description |
|---|---|---|---|
| 1 | `activity_id` | str, PK | Primary key, unique activity measurement ID |
| 2 | `molecule_id` | str, FK | FK to molecule (from API `molecule_chembl_id`) |
| 3 | `assay_id` | str, FK | FK to assay (from API `assay_chembl_id`) |
| 4 | `target_id` | str, FK | FK to target (from API `target_chembl_id`) |
| 5 | `publication_id` | str, FK | FK to publication (from API `document_chembl_id`) |
| 6 | `record_id` | int | FK to compound_record |
| 7 | `src_id` | int | Data source ID |
| 8 | `standard_type` | str | Measurement type (IC50, Ki, etc.) |
| 9 | `standard_value` | float | Standardized numeric value |
| 10 | `standard_units` | str | Standardized units (nM, uM, etc.) |
| 11 | `standard_relation` | str | Relation operator (=, <, >, etc.) |
| 12 | `standard_flag` | int | Standardization flag (0/1) |
| 13 | `standard_upper_value` | float | Standardized upper bound |
| 14 | `standard_text_value` | str | Standardized text value |
| 15 | `pchembl_value` | float | -log10 molar activity (0-14) |
| 16 | `type` | str | Original measurement type |
| 17 | `value` | float | Original numeric value |
| 18 | `units` | str | Original units |
| 19 | `relation` | str | Original operator |
| 20 | `upper_value` | float | Original upper bound |
| 21 | `text_value` | str | Original text value |
| 22 | `canonical_smiles` | str | Molecule SMILES (denormalized) |
| 23 | `molecule_pref_name` | str | Molecule name (denormalized) |
| 24 | `parent_molecule_id` | str | Parent molecule ChEMBL ID (denormalized) |
| 25 | `target_pref_name` | str | Target name (denormalized) |
| 26 | `target_organism` | str | Target organism (denormalized) |
| 27 | `taxonomy_id` | float | NCBI Taxonomy ID (from API `target_tax_id`) |
| 28 | `assay_type` | str | Assay type code (denormalized) |
| 29 | `assay_description` | str | Assay description (denormalized) |
| 30 | `assay_variant_accession` | str | Variant accession (denormalized) |
| 31 | `assay_variant_mutation` | str | Variant mutation (denormalized) |
| 32 | `bao_endpoint` | str | BAO endpoint ID |
| 33 | `bao_format` | str | BAO format ID |
| 34 | `bao_label` | str | BAO label |
| 35 | `qudt_units` | str | QUDT unit URI |
| 36 | `uo_units` | str | Units Ontology ID |
| 37 | `journal` | str | Publication journal (from API `document_journal`) |
| 38 | `publication_doi` | str | Publication DOI |
| 39 | `publication_pmid` | str | PubMed ID |
| 40 | `publication_pmc_id` | str | PubMed Central ID |
| 41 | `publication_year` | int | Publication year (from API `document_year`) |
| 42 | `activity_comment` | str | Activity textual comment |
| 43 | `data_validity_comment` | str | Data quality comment |
| 44 | `data_validity_description` | str | Data validity explanation |
| 45 | `potential_duplicate` | int | Duplicate flag (0/1) |
| 46 | `toid` | float | Test Occasion ID |
| 47 | `manual_curation_flag` | float | Manual curation flag (0/1) |
| 48 | `original_activity_id` | float | FK to original activity |
| 49 | `ligand_efficiency_bei` | float | Binding Efficiency Index |
| 50 | `ligand_efficiency_le` | float | Ligand Efficiency |
| 51 | `ligand_efficiency_lle` | float | Lipophilic Ligand Efficiency |
| 52 | `ligand_efficiency_sei` | float | Surface Efficiency Index |
| 53 | `action_type` | str | Action classification |
| 54 | `action_type_description` | str | Action type description |
| 55 | `action_type_parent_type` | str | Parent action type category |
| 56 | `activity_properties` | str (JSON) | Activity properties array |

*Plus 6 ETL lineage fields from BaseEntity (entity_id, content_hash, run_id, run_type, ingestion_ts, source_batch_id)*

### 2.2 Assay Pipeline (37 fields)

| # | Silver Field Name | Type | Description |
|---|---|---|---|
| 1 | `assay_id` | str, PK | Primary key, ChEMBL assay ID |
| 2 | `target_id` | str, FK | FK to target (from API `target_chembl_id`) |
| 3 | `publication_id` | str, FK | FK to publication (from API `document_chembl_id`) |
| 4 | `cell_id` | str, FK | FK to cell_line (from API `cell_chembl_id`) |
| 5 | `tissue_id` | str, FK | FK to tissue (from API `tissue_chembl_id`) |
| 6 | `src_id` | int | Data source ID |
| 7 | `src_assay_id` | str | Original source assay ID |
| 8 | `aidx` | str | Assay index |
| 9 | `assay_type` | str | Assay type code (B/F/A/T/P/U) |
| 10 | `assay_type_description` | str | Full assay type description |
| 11 | `assay_category` | str | Assay category |
| 12 | `assay_test_type` | str | Test type (In vivo/In vitro/Ex vivo) |
| 13 | `assay_group` | str | Assay group |
| 14 | `assay_organism` | str | Organism used in assay |
| 15 | `taxonomy_id` | float | NCBI Taxonomy ID (from API `assay_tax_id`) |
| 16 | `assay_cell_type` | str | Cell type |
| 17 | `assay_tissue` | str | Tissue type |
| 18 | `assay_strain` | str | Strain |
| 19 | `assay_subcellular_fraction` | str | Subcellular fraction |
| 20 | `bao_format` | str | BAO format ID |
| 21 | `bao_label` | str | BAO label |
| 22 | `description` | str | Assay description |
| 23 | `confidence_score` | int | Target confidence (0-9) |
| 24 | `confidence_description` | str | Confidence description |
| 25 | `relationship_type` | str | Target-assay relationship type |
| 26 | `relationship_description` | str | Relationship description |
| 27 | `assay_pref_name` | str | Assay preferred name |
| 28 | `score` | float | Assay score |
| 29 | `variant_accession` | str | Variant protein accession |
| 30 | `variant_isoform` | str | Variant isoform ID |
| 31 | `variant_mutation` | str | Variant mutation (e.g. V600E) |
| 32 | `variant_organism` | str | Variant organism |
| 33 | `variant_sequence` | str | Variant amino acid sequence |
| 34 | `variant_taxonomy_id` | float | Variant taxonomy ID |
| 35 | `variant_sequence_json` | str (JSON) | Original variant data |
| 36 | `assay_classifications` | str (JSON) | Assay classifications |
| 37 | `assay_parameters` | str (JSON) | Assay parameters |

### 2.3 Target Pipeline (17 fields)

| # | Silver Field Name | Type | Description |
|---|---|---|---|
| 1 | `target_id` | str, PK | Primary key, ChEMBL target ID |
| 2 | `pref_name` | str | Preferred target name |
| 3 | `target_type` | str | Target type classification |
| 4 | `organism` | str | Target organism |
| 5 | `taxonomy_id` | float | NCBI Taxonomy ID (from API `tax_id`) |
| 6 | `species_group_flag` | bool | Species group flag |
| 7 | `downgraded` | bool | Deprecated/downgraded flag |
| 8 | `primary_component_id` | float | First component ID (join key) |
| 9 | `target_components` | str (JSON) | Full component data |
| 10 | `target_component_synonyms` | str (JSON) | Aggregated synonyms |
| 11 | `cross_references` | str (JSON) | Component cross-references |
| 12 | `pipeline_stages` | str (JSON) | Drug pipeline stages |
| 13 | `component_accessions` | object (list) | Component UniProt accessions |
| 14 | `component_ids` | object (list) | Component IDs |
| 15 | `component_types` | object (list) | Component types |
| 16 | `component_relationships` | object (list) | Component relationships |
| 17 | `component_descriptions` | object (list) | Component descriptions |

### 2.4 Molecule Pipeline (56 fields)

| # | Silver Field Name | Type | Description |
|---|---|---|---|
| 1 | `molecule_id` | str, PK | Primary key, ChEMBL molecule ID |
| 2 | `pref_name` | str | Preferred molecule name |
| 3 | `molecule_type` | str | Molecule type classification |
| 4 | `structure_type` | str | Structure type (MOL/SEQ/BOTH/NONE) |
| 5 | `max_phase` | float | Max clinical phase (-1 to 4) |
| 6 | `first_approval` | float | Year of first approval |
| 7 | `oral` | bool | Oral administration flag |
| 8 | `parenteral` | bool | Parenteral administration flag |
| 9 | `topical` | bool | Topical administration flag |
| 10 | `therapeutic_flag` | bool | Therapeutic use flag |
| 11 | `withdrawn_flag` | bool | Withdrawn drug flag |
| 12 | `black_box_warning` | int | Black box warning (0/1) |
| 13 | `natural_product` | int | Natural product (-1/0/1) |
| 14 | `first_in_class` | int | First in class (-1/0/1) |
| 15 | `prodrug` | int | Prodrug flag (-1/0/1) |
| 16 | `inorganic_flag` | int | Inorganic flag (-1/0/1) |
| 17 | `polymer_flag` | int | Polymer flag (0/1) |
| 18 | `chirality` | int | Chirality (-1/0/1/2) |
| 19 | `dosed_ingredient` | int | Dosed ingredient (0/1) |
| 20 | `availability_type` | float | Availability (-2 to 2) |
| 21 | `usan_stem` | str | USAN stem name |
| 22 | `usan_stem_definition` | str | USAN stem definition |
| 23 | `usan_substem` | str | USAN substem |
| 24 | `usan_year` | float | USAN year |
| 25 | `helm_notation` | str | HELM biopolymer notation |
| 26 | `molecule_species` | str | Species (ACID/BASE/NEUTRAL) |
| 27 | `hierarchy_parent_chembl_id` | str | Parent molecule in hierarchy |
| 28 | `hierarchy_active_chembl_id` | str | Active form in hierarchy |
| 29 | `hierarchy_child_chembl_id` | str | Child molecule in hierarchy |
| 30 | `property_alogp` | float | ALogP value |
| 31 | `property_full_mwt` | float | Full molecular weight |
| 32 | `property_mw_freebase` | float | Freebase molecular weight |
| 33 | `property_hba` | int | H-bond acceptor count |
| 34 | `property_hbd` | int | H-bond donor count |
| 35 | `property_psa` | float | Polar surface area |
| 36 | `property_rtb` | int | Rotatable bond count |
| 37 | `property_heavy_atoms` | int | Heavy atom count |
| 38 | `property_aromatic_rings` | int | Aromatic ring count |
| 39 | `property_ro5_violations` | int | Lipinski violations (0-4) |
| 40 | `property_qed_weighted` | float | QED drug-likeness (0-1) |
| 41 | `property_full_molformula` | str | Molecular formula |
| 42 | `property_ro3_pass` | str | Rule-of-3 (Y/N) |
| 43 | `logp` | float | Alias for property_alogp |
| 44 | `logp_method` | str | LogP method (alogp/xlogp) |
| 45 | `molecular_weight` | float | Alias for property_full_mwt |
| 46 | `polar_surface_area` | float | Alias for property_psa |
| 47 | `rotatable_bond_count` | int | Alias for property_rtb |
| 48 | `heavy_atom_count` | int | Alias for property_heavy_atoms |
| 49 | `hba_count` | int | Alias for property_hba |
| 50 | `hbd_count` | int | Alias for property_hbd |
| 51 | `aromatic_ring_count` | int | Alias for property_aromatic_rings |
| 52 | `canonical_smiles` | str | Canonical SMILES |
| 53 | `standard_inchi` | str | Standard InChI |
| 54 | `inchi_key` | str | InChI Key (27-char) |
| 55 | `molecule_hierarchy` | str (JSON) | Hierarchy JSON |
| 56 | `molecule_properties` | str (JSON) | Properties JSON |
| 57 | `molecule_structures` | str (JSON) | Structures JSON |
| 58 | `molecule_synonyms` | str (JSON) | Synonyms JSON |
| 59 | `cross_references` | str (JSON) | Cross-references JSON |
| 60 | `atc_classifications` | str (JSON) | ATC classifications JSON |

---

## 3. Cross-Pipeline Field Mapping Table

Rows = unified field concept. Columns = current field name in each pipeline.
`-` = field not present in pipeline. `[denorm]` = denormalized from another entity.

### 3.1 Primary & Foreign Keys

| Unified Field | Activity | Assay | Target | Molecule | API Source | Inconsistency |
|---|---|---|---|---|---|---|
| `activity_id` | `activity_id` (PK) | - | - | - | `activity_id` | - |
| `assay_id` | `assay_id` (FK) | `assay_id` (PK) | - | - | `assay_chembl_id` | OK |
| `target_id` | `target_id` (FK) | `target_id` (FK) | `target_id` (PK) | - | `target_chembl_id` | OK |
| `molecule_id` | `molecule_id` (FK) | - | - | `molecule_id` (PK) | `molecule_chembl_id` | OK |
| `publication_id` | `publication_id` (FK) | `publication_id` (FK) | - | - | `document_chembl_id` | OK |
| `cell_id` | - | `cell_id` (FK) | - | - | `cell_chembl_id` | OK |
| `tissue_id` | - | `tissue_id` (FK) | - | - | `tissue_chembl_id` | OK |
| `src_id` | `src_id` | `src_id` | - | - | `src_id` | OK |
| `record_id` | `record_id` | - | - | - | `record_id` | OK |
| `parent_molecule_id` | `parent_molecule_id` [denorm] | - | - | `hierarchy_parent_chembl_id` | `parent_molecule_chembl_id` / `molecule_hierarchy.parent_chembl_id` | **INCONSISTENT** |

### 3.2 Taxonomy & Organism

| Unified Field | Activity | Assay | Target | Molecule | API Source | Inconsistency |
|---|---|---|---|---|---|---|
| `taxonomy_id` | `taxonomy_id` | `taxonomy_id` | `taxonomy_id` | - | Activity: `target_tax_id`; Assay: `assay_tax_id`; Target: `tax_id` | **Silver OK, but API sources vary; DTO TargetRecord still uses `tax_id`** |
| `organism` | `target_organism` [denorm] | `assay_organism` | `organism` | - | `target_organism` / `assay_organism` / `organism` | **INCONSISTENT**: bare vs entity-prefixed |
| `variant_taxonomy_id` | - | `variant_taxonomy_id` | - | - | `variant_sequence.tax_id` | OK |

### 3.3 Preferred Name & Description

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| `pref_name` (entity name) | `target_pref_name` / `molecule_pref_name` [denorm] | `assay_pref_name` | `pref_name` | `pref_name` | **INCONSISTENT**: Target/Molecule use bare `pref_name`, Assay uses `assay_pref_name`; Activity denormalizes with source prefix |
| `description` | `assay_description` [denorm] | `description` | - | - | **INCONSISTENT**: Assay uses bare `description`, Activity denormalizes as `assay_description` |

### 3.4 Type Classification

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| Entity type | - | `assay_type` | `target_type` | `molecule_type` | OK (consistently prefixed with entity name) |
| Entity type description | - | `assay_type_description` | - | - | Assay-specific |

### 3.5 BioAssay Ontology (BAO)

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| `bao_endpoint` | `bao_endpoint` | - | - | - | Activity-specific |
| `bao_format` | `bao_format` | `bao_format` | - | - | OK |
| `bao_label` | `bao_label` | `bao_label` | - | - | OK |

### 3.6 Variant Information

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| Variant accession | `assay_variant_accession` [denorm] | `variant_accession` | - | - | **INCONSISTENT**: Activity prefixes with `assay_`, Assay uses bare `variant_*` |
| Variant mutation | `assay_variant_mutation` [denorm] | `variant_mutation` | - | - | **INCONSISTENT**: same as above |
| Variant isoform | - | `variant_isoform` | - | - | Assay-specific |
| Variant organism | - | `variant_organism` | - | - | Assay-specific |
| Variant sequence | - | `variant_sequence` | - | - | Assay-specific |
| Variant taxonomy ID | - | `variant_taxonomy_id` | - | - | Assay-specific |
| Variant JSON | - | `variant_sequence_json` | - | - | Assay-specific |

### 3.7 Chemical Structure (Molecule-centric)

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| `canonical_smiles` | `canonical_smiles` [denorm] | - | - | `canonical_smiles` | OK |
| `standard_inchi` | - | - | - | `standard_inchi` | Molecule-specific |
| `inchi_key` | - | - | - | `inchi_key` | Molecule-specific |

### 3.8 Publication Data (denormalized in Activity)

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| `journal` | `journal` | - | - | - | From API `document_journal` |
| `publication_year` | `publication_year` | - | - | - | From API `document_year` |
| `publication_doi` | `publication_doi` | - | - | - | Activity-specific |
| `publication_pmid` | `publication_pmid` | - | - | - | Activity-specific |
| `publication_pmc_id` | `publication_pmc_id` | - | - | - | Activity-specific |

### 3.9 Cross-References & Complex Fields (JSON)

| Unified Field | Activity | Assay | Target | Molecule | Inconsistency |
|---|---|---|---|---|---|
| Cross-references | - | - | `cross_references` | `cross_references` | OK |
| Activity properties | `activity_properties` | - | - | - | - |
| Assay classifications | - | `assay_classifications` | - | - | - |
| Assay parameters | - | `assay_parameters` | - | - | - |
| Target components | - | - | `target_components` | - | - |
| Target synonyms | - | - | `target_component_synonyms` | - | - |
| Pipeline stages | - | - | `pipeline_stages` | - | - |
| Molecule hierarchy | - | - | - | `molecule_hierarchy` | - |
| Molecule properties | - | - | - | `molecule_properties` | - |
| Molecule structures | - | - | - | `molecule_structures` | - |
| Molecule synonyms | - | - | - | `molecule_synonyms` | - |
| ATC classifications | - | - | - | `atc_classifications` | - |

### 3.10 Quality & Curation (Activity-specific)

| Unified Field | Activity | Assay | Target | Molecule |
|---|---|---|---|---|
| `data_validity_comment` | `data_validity_comment` | - | - | - |
| `data_validity_description` | `data_validity_description` | - | - | - |
| `activity_comment` | `activity_comment` | - | - | - |
| `potential_duplicate` | `potential_duplicate` | - | - | - |
| `manual_curation_flag` | `manual_curation_flag` | - | - | - |
| `original_activity_id` | `original_activity_id` | - | - | - |
| `toid` | `toid` | - | - | - |

### 3.11 Flags (Molecule-specific)

| Unified Field | Activity | Assay | Target | Molecule |
|---|---|---|---|---|
| `oral` | - | - | - | `oral` |
| `parenteral` | - | - | - | `parenteral` |
| `topical` | - | - | - | `topical` |
| `therapeutic_flag` | - | - | - | `therapeutic_flag` |
| `withdrawn_flag` | - | - | - | `withdrawn_flag` |
| `black_box_warning` | - | - | - | `black_box_warning` |
| `natural_product` | - | - | - | `natural_product` |
| `first_in_class` | - | - | - | `first_in_class` |
| `prodrug` | - | - | - | `prodrug` |
| `inorganic_flag` | - | - | - | `inorganic_flag` |
| `polymer_flag` | - | - | - | `polymer_flag` |
| `chirality` | - | - | - | `chirality` |
| `dosed_ingredient` | - | - | - | `dosed_ingredient` |
| `availability_type` | - | - | - | `availability_type` |

### 3.12 Target Component Fields (Target-specific)

| Unified Field | Activity | Assay | Target | Molecule |
|---|---|---|---|---|
| `primary_component_id` | - | - | `primary_component_id` | - |
| `component_accessions` | - | - | `component_accessions` | - |
| `component_ids` | - | - | `component_ids` | - |
| `component_types` | - | - | `component_types` | - |
| `component_relationships` | - | - | `component_relationships` | - |
| `component_descriptions` | - | - | `component_descriptions` | - |
| `species_group_flag` | - | - | `species_group_flag` | - |
| `downgraded` | - | - | `downgraded` | - |

### 3.13 Confidence & Relationship (Assay-specific)

| Unified Field | Activity | Assay | Target | Molecule |
|---|---|---|---|---|
| `confidence_score` | - | `confidence_score` | - | - |
| `confidence_description` | - | `confidence_description` | - | - |
| `relationship_type` | - | `relationship_type` | - | - |
| `relationship_description` | - | `relationship_description` | - | - |
| `score` | - | `score` | - | - |

---

## 4. Identified Inconsistencies

### 4.1 CRITICAL: `taxonomy_id` API-to-Silver rename varies by pipeline

| Pipeline | API Field | Silver Field | DTO Field |
|---|---|---|---|
| Activity | `target_tax_id` | `taxonomy_id` | `target_tax_id` (DTO lags) |
| Assay | `assay_tax_id` | `taxonomy_id` | `assay_tax_id` (DTO lags) |
| Target | `tax_id` | `taxonomy_id` | `tax_id` (DTO lags) |

**Problem:** Silver layer is unified (`taxonomy_id`), but DTOs still use legacy API names.
**Recommendation:** Align DTO field names with Silver convention: use `taxonomy_id` everywhere.

### 4.2 HIGH: `organism` naming is entity-prefixed inconsistently

| Pipeline | Silver Field | Convention |
|---|---|---|
| Activity | `target_organism` | Source entity prefix (denormalized) |
| Assay | `assay_organism` | Entity prefix |
| Target | `organism` | **Bare** (no prefix) |

**Recommendation:** Within each entity's own pipeline, use bare `organism`.
For denormalized fields in Activity, prefix with source entity (`target_organism`, etc.).
**Target pipeline should keep `organism`** (it IS the target's own field).

### 4.3 HIGH: `pref_name` naming is inconsistent

| Pipeline | Silver Field | Convention |
|---|---|---|
| Activity | `molecule_pref_name`, `target_pref_name` | Source entity prefix (denormalized) |
| Assay | `assay_pref_name` | **Entity prefix even for own field** |
| Target | `pref_name` | Bare |
| Molecule | `pref_name` | Bare |

**Problem:** Assay uses `assay_pref_name` for its own preferred name, while Target and Molecule use bare `pref_name`.
**Recommendation:** Use bare `pref_name` in each entity's own pipeline (Assay should use `pref_name`).
Denormalized fields in Activity should use source prefix (`target_pref_name`, `molecule_pref_name`).

### 4.4 HIGH: `description` naming inconsistent

| Pipeline | Silver Field | Convention |
|---|---|---|
| Activity | `assay_description` | Denormalized with source prefix |
| Assay | `description` | **Bare** (no entity prefix) |

**Problem:** This is actually correct but creates confusion. When Activity denormalizes Assay's `description`, it becomes `assay_description` -- which is the right convention for denormalization.
**Recommendation:** Keep as-is. This pattern is intentional.

### 4.5 MEDIUM: Variant field naming diverges between Assay and Activity

| Concept | Activity (denormalized) | Assay (native) |
|---|---|---|
| Accession | `assay_variant_accession` | `variant_accession` |
| Mutation | `assay_variant_mutation` | `variant_mutation` |

**Problem:** Activity uses `assay_variant_*` prefix (double prefix: `assay_` + `variant_`).
**Recommendation:** Keep current convention. Denormalized fields in Activity should indicate source entity.

### 4.6 MEDIUM: Molecule backward-compatible aliases create dual-naming

Property fields exist in two forms:

| Canonical (property_*) | Alias | Source |
|---|---|---|
| `property_alogp` | `logp` | ALogP |
| `property_full_mwt` | `molecular_weight` | Full MW |
| `property_hba` | `hba_count` | HBA |
| `property_hbd` | `hbd_count` | HBD |
| `property_psa` | `polar_surface_area` | PSA |
| `property_rtb` | `rotatable_bond_count` | RTB |
| `property_heavy_atoms` | `heavy_atom_count` | Heavy atoms |
| `property_aromatic_rings` | `aromatic_ring_count` | Aromatic rings |

**Problem:** Both canonical and alias fields exist simultaneously, doubling the column count.
**Recommendation:** Deprecate aliases in future version; keep `property_*` as canonical. Or choose one convention and drop the other.

### 4.7 LOW: `parent_molecule_id` vs `hierarchy_parent_chembl_id`

| Pipeline | Field | Source |
|---|---|---|
| Activity | `parent_molecule_id` | API `parent_molecule_chembl_id` (denormalized) |
| Molecule | `hierarchy_parent_chembl_id` | API `molecule_hierarchy.parent_chembl_id` |

**Problem:** Same concept (parent molecule), different naming. Activity uses `parent_molecule_id`, Molecule uses `hierarchy_parent_chembl_id`.
**Recommendation:** Standardize to `parent_molecule_id` and `hierarchy_parent_chembl_id` serving different purposes (Activity denormalizes the direct FK, Molecule stores the full hierarchy).

### 4.8 LOW: DTO JSON field naming convention

| Layer | Activity Properties | Assay Classifications |
|---|---|---|
| DTO | `activity_properties_json` | `assay_classifications_json` |
| Silver Schema | `activity_properties` | `assay_classifications` |
| Domain Entity | `activity_properties` | `assay_classifications` |

**Problem:** DTOs append `_json` suffix to JSON fields, Silver/Entity layers do not.
**Recommendation:** Align. Either drop `_json` suffix in DTOs or add it everywhere.

---

## 5. Unified Naming Convention Proposal

### 5.1 Rules

1. **Primary keys**: `{entity}_id` (e.g., `activity_id`, `assay_id`, `target_id`, `molecule_id`)
2. **Foreign keys**: `{referenced_entity}_id` (e.g., `target_id`, `publication_id`)
3. **NCBI Taxonomy**: Always `taxonomy_id` at Silver layer (regardless of API source name)
4. **Entity's own fields**: Use bare names without entity prefix (`pref_name`, `organism`, `description`)
5. **Denormalized fields**: Prefix with source entity (`target_pref_name`, `assay_description`)
6. **Nested flattened fields**: Use group prefix (`property_*`, `hierarchy_*`, `variant_*`, `ligand_efficiency_*`)
7. **JSON serialized fields**: No `_json` suffix at Silver layer
8. **Type classification**: `{entity}_type` (already consistent)

### 5.2 Changes Required

| Current | Proposed | Pipeline | Impact |
|---|---|---|---|
| DTO `tax_id` | DTO `taxonomy_id` | Target DTO | LOW (DTO internal) |
| DTO `assay_tax_id` | DTO `taxonomy_id` | Assay DTO | LOW (DTO internal) |
| DTO `target_tax_id` | DTO `taxonomy_id` | Activity DTO | LOW (DTO internal) |
| DTO `*_json` suffix | Drop `_json` | All DTOs | MEDIUM (DTO→Entity alignment) |
| `assay_pref_name` → `pref_name` | `pref_name` | Assay Silver | HIGH (schema change, downstream) |
| Keep `property_*` canonical | Deprecate aliases | Molecule Silver | HIGH (remove 9 alias fields) |

---

## 6. Data Validation Rules (Cross-Pipeline)

### 6.1 Referential Integrity

| FK Field | Source Pipeline | Target Pipeline | Validation |
|---|---|---|---|
| `activity.assay_id` | activity | assay | Must match `assay.assay_id` |
| `activity.molecule_id` | activity | molecule | Must match `molecule.molecule_id` |
| `activity.target_id` | activity | target | Must match `target.target_id` (nullable) |
| `activity.publication_id` | activity | publication | Must match `publication.publication_id` (nullable) |
| `assay.target_id` | assay | target | Must match `target.target_id` (nullable) |
| `assay.publication_id` | assay | publication | Must match `publication.publication_id` (nullable) |

### 6.2 taxonomy_id Consistency

When `taxonomy_id` appears across pipelines for the same entity reference:
- `activity.taxonomy_id` should match `target.taxonomy_id` for the same `target_id`
- `assay.taxonomy_id` is assay-specific (may differ from target taxonomy)

### 6.3 Denormalized Field Consistency

Activity denormalized fields should match source entity data:
- `activity.target_pref_name` == `target.pref_name` (for same `target_id`)
- `activity.target_organism` == `target.organism` (for same `target_id`)
- `activity.canonical_smiles` == `molecule.canonical_smiles` (for same `molecule_id`)
- `activity.assay_type` == `assay.assay_type` (for same `assay_id`)

---

## 7. Summary Statistics

| Metric | Activity | Assay | Target | Molecule |
|---|---|---|---|---|
| Total Silver fields (excl. lineage) | 56 | 37 | 17 | 60 |
| Primary key fields | 1 | 1 | 1 | 1 |
| Foreign key fields | 4 | 5 | 0 | 0 |
| Denormalized fields | 10 | 0 | 0 | 0 |
| JSON serialized fields | 1 | 3 | 4 | 6 |
| Fields shared with other pipelines | 6 | 4 | 0 | 1 |
| Fields requiring rename | 0 | 1 (`assay_pref_name`) | 0 | 0 (9 aliases to deprecate) |
| DTO fields requiring rename | 1 | 1 | 1 | 6 |
| Naming inconsistencies found | 2 | 3 | 1 | 1 |
