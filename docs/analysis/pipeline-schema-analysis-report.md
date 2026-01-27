# Pipeline Schema Analysis Report

**Date**: 2026-01-26
**Version**: 1.0
**Author**: Claude Code Analysis

---

## Executive Summary

This report analyzes the field extraction schemas across all 7 data providers (ChEMBL, PubChem, UniProt, CrossRef, OpenAlex, PubMed, SemanticScholar) in the BioETL pipeline. The analysis compares pipeline schemas with provider API schemas to identify discrepancies, missing fields, and potential extraction errors.

---

## Table of Contents

1. [ChEMBL Pipeline Analysis](#1-chembl-pipeline-analysis)
2. [PubChem Pipeline Analysis](#2-pubchem-pipeline-analysis)
3. [UniProt Pipeline Analysis](#3-uniprot-pipeline-analysis)
4. [CrossRef Pipeline Analysis](#4-crossref-pipeline-analysis)
5. [OpenAlex Pipeline Analysis](#5-openalex-pipeline-analysis)
6. [PubMed Pipeline Analysis](#6-pubmed-pipeline-analysis)
7. [SemanticScholar Pipeline Analysis](#7-semanticscholar-pipeline-analysis)
8. [Identified Discrepancies](#8-identified-discrepancies)
9. [Correction Prompts](#9-correction-prompts)

---

## 1. ChEMBL Pipeline Analysis

### 1.1 Activity Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/chembl/activity.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `activity_id` |
| **Foreign Keys** | `assay_chembl_id`, `molecule_chembl_id`, `target_chembl_id`, `document_chembl_id` |
| **Standardized Values** | `standard_relation`, `standard_value`, `standard_units`, `standard_type`, `standard_flag` |
| **Derived Metrics** | `pchembl_value` |
| **Quality Fields** | `data_validity_comment`, `activity_comment`, `potential_duplicate` |
| **Ontologies** | `bao_endpoint`, `uo_units`, `qudt_units` |
| **Original Values** | `src_id`, `record_id`, `type`, `relation`, `value`, `units`, `text_value`, `standard_text_value`, `upper_value`, `standard_upper_value`, `toid` |
| **Ligand Efficiency** | `ligand_efficiency_bei`, `ligand_efficiency_le`, `ligand_efficiency_lle`, `ligand_efficiency_sei` |
| **Action Type** | `action_type_action_type`, `action_type_description`, `action_type_parent_type` |
| **Molecule/Target** | `canonical_smiles`, `molecule_pref_name`, `parent_molecule_chembl_id`, `target_pref_name`, `target_organism`, `target_taxonomy_id` |
| **Assay Info** | `assay_type`, `assay_description`, `assay_variant_accession`, `assay_variant_mutation`, `bao_format`, `bao_label` |
| **Document** | `document_journal`, `document_year` |
| **JSON** | `activity_properties` |

**ChEMBL API Provides** (per `/activity/schema`):
- All fields above PLUS:
  - `data_validity_description` (missing extraction)
  - `manual_curation_flag` (commented out in schema)
  - `original_activity_id` (commented out in schema)
  - `ridx` (record index, commented out)

**Discrepancies**:
1. `data_validity_description` - API provides, not extracted
2. `manual_curation_flag` - Commented out but available
3. `original_activity_id` - Commented out but available

### 1.2 Molecule Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/chembl/molecule.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `molecule_chembl_id` |
| **Identifiers** | `structure_standard_inchi_key`, `inchikey` |
| **Core Properties** | `pref_name`, `max_phase`, `structure_type`, `molecule_type`, `first_approval` |
| **Flags** | `therapeutic_flag`, `oral`, `parenteral`, `topical`, `black_box_warning`, `natural_product`, `first_in_class`, `prodrug`, `inorganic_flag`, `polymer_flag`, `withdrawn_flag`, `chirality`, `dosed_ingredient`, `availability_type` |
| **USAN** | `usan_year`, `usan_stem`, `usan_substem`, `usan_stem_definition` |
| **Other** | `helm_notation`, `molecule_species` |
| **Hierarchy** | `hierarchy_parent_chembl_id`, `hierarchy_active_chembl_id`, `hierarchy_child_chembl_id` |
| **Properties** | `property_alogp`, `property_mw_freebase`, `property_full_mwt`, `property_hba`, `property_hbd`, `property_psa`, `property_rtb`, `property_ro5_violations`, `property_heavy_atoms`, `property_aromatic_rings`, `property_qed_weighted`, `property_full_molformula`, `property_ro3_pass` |
| **Structures** | `canonical_smiles`, `standard_inchi` |
| **JSON** | `molecule_hierarchy`, `molecule_properties`, `molecule_structures`, `molecule_synonyms`, `cross_references`, `atc_classifications` |

**ChEMBL API Missing Fields** (Available but not extracted):
1. `molregno` - Internal database ID (commented out)
2. `chebi_id`, `chebi_par_id` - ChEBI identifiers (commented out)
3. `downgraded`, `nomerge` flags (commented out)
4. Additional properties: `cx_logd`, `cx_logp`, `cx_most_apka`, `cx_most_bpka`, `molecular_species`, `mw_monoisotopic`, `np_likeness_score`, `num_lipinski_ro5_violations`, `num_ro5_violations`

### 1.3 Target Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/chembl/target.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `target_chembl_id` |
| **Classification** | `target_type` |
| **Metadata** | `pref_name`, `description`, `taxonomy_id`, `organism`, `species_group_flag`, `downgraded`, `dap_id` |
| **Components (Lists)** | `component_accessions`, `component_ids`, `component_types`, `component_relationships`, `component_descriptions`, `component_organisms`, `component_taxonomy_ids` |
| **JSON** | `target_components`, `cross_references`, `pipeline_stages`, `target_constraints`, `target_component_synonyms` |

**Missing from API**:
1. `tid` - Internal target ID (commented out)
2. `target_parent_type` - Higher-level classification (commented out)

### 1.4 Assay Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/chembl/assay.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `assay_chembl_id` |
| **Classification** | `description`, `assay_type`, `assay_test_type`, `assay_category`, `assay_group` |
| **Biological Context** | `assay_organism`, `assay_taxonomy_id`, `assay_strain`, `assay_tissue`, `assay_cell_type`, `assay_subcellular_fraction` |
| **Target** | `target_chembl_id`, `relationship_type`, `relationship_description`, `confidence_score`, `confidence_description` |
| **Metadata** | `src_id`, `src_assay_id`, `document_chembl_id`, `assay_pref_name`, `score` |
| **Foreign Keys** | `cell_chembl_id`, `tissue_chembl_id` |
| **BAO** | `bao_format`, `bao_label` |
| **Variant** | `variant_accession`, `variant_isoform`, `variant_mutation`, `variant_organism`, `variant_sequence`, `variant_taxonomy_id`, `variant_sequence_json` |
| **JSON** | `assay_classifications`, `assay_parameters` |

**Missing**:
1. `assay_id` - Internal ID (commented out)
2. `curated_by`, `activity_count` (commented out)
3. `a2t_complex`, `a2t_multi` - Assay-to-target flags
4. `mc_*` fields - Multi-component fields (commented out)
5. `aidx`, `ridx`, `tid_fixed`, `variant_id` (partially commented)

---

## 2. PubChem Pipeline Analysis

### 2.1 Compound Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/pubchem/compound.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `cid` |
| **Structural IDs** | `canonical_smiles`, `isomeric_smiles`, `inchi`, `inchi_key` |
| **Nomenclature** | `molecular_formula`, `iupac_name` |
| **Physical Properties** | `molecular_weight`, `exact_mass` |
| **Computed Descriptors** | `xlogp`, `tpsa`, `complexity`, `charge` |
| **Atom/Bond Counts** | `heavy_atom_count`, `h_bond_donor_count`, `h_bond_acceptor_count`, `rotatable_bond_count` |
| **Stereochemistry** | `atom_stereo_count`, `defined_atom_stereo_count`, `undefined_atom_stereo_count`, `bond_stereo_count`, `defined_bond_stereo_count`, `undefined_bond_stereo_count`, `isotope_atom_count`, `covalent_unit_count` |
| **3D Properties** | `volume_3d`, `conformer_count_3d`, `feature_acceptor_count_3d`, `feature_donor_count_3d`, `feature_anion_count_3d`, `feature_cation_count_3d`, `feature_ring_count_3d`, `feature_hydrophobe_count_3d`, `effective_rotor_count_3d`, `conformer_rmsd_3d` |

**PubChem API Full Property List** (45 properties available):
1. CID, MolecularFormula, MolecularWeight, CanonicalSMILES, IsomericSMILES
2. InChI, InChIKey, IUPACName, XLogP, ExactMass, MonoisotopicMass
3. TPSA, Complexity, Charge, HBondDonorCount, HBondAcceptorCount
4. RotatableBondCount, HeavyAtomCount
5. AtomStereoCount, DefinedAtomStereoCount, UndefinedAtomStereoCount
6. BondStereoCount, DefinedBondStereoCount, UndefinedBondStereoCount
7. CovalentUnitCount, Volume3D
8. XStericQuadrupole3D, YStericQuadrupole3D, ZStericQuadrupole3D (NOT EXTRACTED)
9. FeatureCount3D (NOT EXTRACTED), FeatureAcceptorCount3D, FeatureDonorCount3D
10. FeatureAnionCount3D, FeatureCationCount3D, FeatureRingCount3D
11. FeatureHydrophobeCount3D, ConformerModelRMSD3D, EffectiveRotorCount3D
12. ConformerCount3D

**Missing Fields**:
1. `MonoisotopicMass` - Similar to ExactMass but different
2. `XStericQuadrupole3D`, `YStericQuadrupole3D`, `ZStericQuadrupole3D` - 3D shape descriptors
3. `FeatureCount3D` - Total 3D feature count
4. Fingerprint data (881 bits)
5. Patent information
6. Synonyms list

---

## 3. UniProt Pipeline Analysis

### 3.1 Protein Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/uniprot/protein.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `accession` |
| **Identifiers** | `entry_name`, `entry_type`, `secondary_accessions` |
| **Protein Names** | `protein_name`, `protein_short_names`, `protein_alternative_names`, `protein_ec_numbers`, `flag` |
| **Gene Names** | `gene_primary`, `gene_synonyms`, `gene_orf_names` |
| **Organism** | `organism_scientific`, `organism_common`, `taxonomy_id`, `lineage` |
| **Evidence** | `protein_existence`, `annotation_score`, `reviewed` |
| **Sequence** | `sequence`, `sequence_length`, `sequence_mass`, `sequence_checksum`, `sequence_modified` |
| **Metadata** | `entry_version`, `entry_created`, `entry_modified` |
| **Functional Annotation** | `function_comment`, `catalytic_activity`, `activity_regulation`, `subunit`, `pathway`, `subcellular_location`, `tissue_specificity`, `alternative_products`, `disease_involvement`, `pharmaceutical_use`, `similarity_comment`, `caution` |
| **Cross-References** | `go_terms`, `drugbank_ids`, `chembl_ids`, `guidetopharmacology_ids` |
| **Features** | `features`, `keywords` |
| **Counts** | `cross_reference_count`, `feature_count`, `keyword_count`, `publication_count`, `isoform_count` |

**UniProt API Additional Fields** (Available but not extracted):
1. `organism.synonyms` - Organism synonym names
2. `organism.host` - Virus host information
3. `virus_host` - Direct virus host data
4. `entryAudit` - Complete audit information
5. `references` - Full publication references list
6. `cofactor` - Cofactor information
7. `biophysicochemical_properties` - pH, temperature optima
8. `induction` - Gene induction information
9. `biotechnology` - Biotechnology applications
10. `disruption_phenotype` - Knockout phenotype data
11. `pharmaceutical` - Pharmaceutical data (separate from pharmaceutical_use)
12. `pdb_xrefs` - PDB structure cross-references
13. `3d_structure` - 3D structure availability
14. All additional cross-reference databases (150+ databases)

---

## 4. CrossRef Pipeline Analysis

### 4.1 Publication Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/crossref/work.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `doi` |
| **Core Fields** | `type`, `title` |
| **Container** | `container_title`, `publisher`, `issn`, `isbn` |
| **Volume/Issue** | `volume`, `issue`, `page` |
| **Dates** | `published_date`, `created_date`, `deposited_date` |
| **Content** | `abstract`, `language`, `subject` |
| **License** | `license_url` |
| **Metrics** | `is_referenced_by_count`, `references_count` |
| **Funding** | `funder_names`, `clinical_trial_numbers` |
| **Policies** | `update_policy` |

**CrossRef API Additional Fields** (Available but not extracted):
1. `author` - Full author list with ORCID, affiliation
2. `editor` - Editor list
3. `translator` - Translator list
4. `contributor` - Other contributors
5. `reference` - Complete reference list
6. `funder` - Detailed funder info with DOI, award numbers
7. `relation` - Related works
8. `assertion` - Publisher assertions
9. `article-number` - Article number (alternative to pages)
10. `original-title` - Original title in original language
11. `subtitle` - Subtitle
12. `short-title` - Short title
13. `group-title` - Group/section title
14. `update-to` - Updated versions
15. `source` - Data source
16. `link` - Full-text links
17. `score` - Relevance score
18. `prefix` - DOI prefix
19. `member` - Publisher member ID
20. `standards-body` - Standards body info
21. `part-number` - Part number
22. `content-domain` - Content domain restrictions

---

## 5. OpenAlex Pipeline Analysis

### 5.1 Publication Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/openalex/publication.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `openalex_id` |
| **Cross-references** | `pmid`, `doi`, `pmc_id` |
| **Core Content** | `title`, `abstract`, `authors` |
| **Metadata** | `journal`, `year`, `publication_date`, `doc_type`, `language` |
| **Metrics** | `citation_count`, `fwci`, `referenced_works_count` |
| **Open Access** | `is_oa`, `oa_status` |
| **Bibliographic** | `issn`, `publisher`, `volume`, `issue` |
| **Quality** | `is_retracted` |
| **Lookup** | `lookup_method`, `original_id`, `_source` |

**OpenAlex API Additional Fields** (Available but not extracted):
1. `corresponding_author_ids` - Corresponding authors
2. `authorships.raw_affiliation_string` - Raw affiliation text
3. `authorships.raw_author_name` - Raw author name
4. `authorships.countries` - Author countries
5. `authorships.institutions.country_code` - Institution country
6. `apc_list`, `apc_paid` - APC information
7. `best_oa_location` - Best OA location details
8. `locations` - All publication locations
9. `topics` - New topics system (replacing concepts)
10. `keywords` - Author-provided keywords
11. `mesh` - MeSH terms (extracted but needs verification)
12. `sustainable_development_goals` - SDG classification
13. `grants` - Grant information
14. `indexed_in` - Indexing databases
15. `ngrams_url` - N-grams URL
16. `cited_by_percentile_year` - Citation percentile
17. `biblio.first_page`, `biblio.last_page` - Page numbers (partially extracted)
18. `primary_topic` - Primary topic classification
19. `related_works` - Related works list
20. `referenced_works` - Full reference list (URLs)
21. `created_date`, `updated_date` - Record dates
22. `abstract_inverted_index` - Raw inverted index

---

## 6. PubMed Pipeline Analysis

### 6.1 Publication Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/pubmed/publication.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `pmid` |
| **Identifiers** | `doi`, `pmc_id` |
| **Content** | `title`, `abstract`, `abstract_structured`, `vernacular_title`, `language` |
| **Journal** | `journal_title`, `journal_iso_abbrev`, `issn`, `journal_issn_type`, `nlm_unique_id`, `country` |
| **Publication** | `medline_pgn`, `year`, `pub_month`, `pub_day`, `publication_status`, `publication_type_list` |
| **Dates** | `date_completed`, `date_revised` |
| **Metadata** | `citation_subset` |
| **Counts** | `author_count`, `mesh_heading_count`, `keyword_count`, `grant_count`, `reference_count`, `chemical_count` |

**PubMed/MEDLINE Additional Fields** (Available but not extracted):
1. `AffiliationInfo` - Full affiliation details
2. `AuthorList` - Detailed author info with identifiers
3. `CollectiveName` - Group/consortium names
4. `Investigator` - Investigator names
5. `DataBankList` - Data bank accession numbers
6. `CommentsCorrectionsList` - Corrections and comments
7. `CoiStatement` - Conflict of interest statement
8. `OtherAbstract` - Abstract in other languages
9. `SpaceFlightMission` - Space flight mission data
10. `SupplMeshList` - Supplementary MeSH concepts
11. `OtherID` - Other database IDs
12. `KeywordList` - Full keyword list with owner
13. `PersonalNameSubjectList` - Personal name subjects
14. `History` dates: `entrez`, `medline`, `pubmed` (beyond accepted/received/revised)
15. `ArticleDate` - Multiple article dates
16. `NumberOfReferences` - Reference count (direct field)
17. `ELocationID` - Additional electronic IDs
18. `Pagination.StartPage`, `Pagination.EndPage` - Separate page fields
19. `ISSN.IssnType` - ISSN type information

---

## 7. SemanticScholar Pipeline Analysis

### 7.1 Publication Entity

**Pipeline Schema** (`src/bioetl/domain/schemas/semanticscholar/publication.py`):

| Field Category | Extracted Fields |
|----------------|------------------|
| **Primary Key** | `paper_id` |
| **Identifiers** | `arxiv_id`, `dblp_id`, `corpus_id`, `doi`, `pmid`, `pmc_id` |
| **Content** | `title`, `abstract`, `tldr`, `authors` |
| **Journal/Venue** | `journal`, `volume`, `pages`, `venue` |
| **Metrics** | `citation_count`, `reference_count`, `influential_citation_count` |
| **Open Access** | `is_oa`, `open_access_url`, `oa_status` |
| **Classification** | `fields_of_study`, `publication_types` |
| **Lookup** | `lookup_method`, `original_id`, `_source` |

**SemanticScholar API Additional Fields** (Available but not extracted):
1. `authors.authorId` - S2 author ID
2. `authors.externalIds` - Author external IDs (ORCID, DBLP)
3. `authors.url` - Author profile URL
4. `authors.aliases` - Author name aliases
5. `authors.hIndex` - Author h-index
6. `citations` - Full citation list with details
7. `references` - Full reference list with details
8. `embedding` - Paper embedding vector
9. `s2FieldsOfStudy` - S2-specific field classification
10. `publicationVenue` - Detailed venue info with ISSN
11. `publicationVenue.alternate_names` - Venue aliases
12. `publicationVenue.url` - Venue URL
13. `isPublisherLicensed` - License status
14. `url` - Paper URL on S2
15. `citationStyles` - Formatted citations (BibTeX, etc.)
16. `journal.pages` - Journal page info (separate)
17. `contexts` - Citation contexts

---

## 8. Identified Discrepancies

### 8.1 Critical Issues

| Provider | Issue | Severity | Impact |
|----------|-------|----------|--------|
| **ChEMBL Activity** | `data_validity_description` not extracted | Medium | Missing DQ metadata |
| **PubChem** | `MonoisotopicMass` not extracted | Low | Missing alternative mass value |
| **PubChem** | 3D steric quadrupole fields missing | Low | Incomplete 3D descriptors |
| **UniProt** | `cofactor`, `biophysicochemical_properties` missing | Medium | Missing functional data |
| **CrossRef** | Full `author` structure not extracted | High | Missing ORCID, affiliations |
| **CrossRef** | `reference` list not extracted | High | Missing citation data |
| **OpenAlex** | `topics` (new system) not extracted | Medium | Using deprecated `concepts` |
| **OpenAlex** | `grants` not extracted | Medium | Missing funding data |
| **PubMed** | `AffiliationInfo` structure incomplete | Medium | Missing detailed affiliations |
| **SemanticScholar** | `embedding` vectors not extracted | Low | Missing ML features |

### 8.2 Field Naming Inconsistencies

| Provider | API Field | Schema Field | Issue |
|----------|-----------|--------------|-------|
| ChEMBL | `target_tax_id` | `target_taxonomy_id` | Renamed (correct) |
| ChEMBL | `assay_tax_id` | `assay_taxonomy_id` | Renamed (correct) |
| PubChem | `HBondDonorCount` | `h_bond_donor_count` | Snake_case (correct) |
| OpenAlex | `cited_by_count` | `citation_count` | Unified naming (correct) |
| OpenAlex | `pmcid` | `pmc_id` | Renamed (correct) |
| SemanticScholar | `citationCount` | `citation_count` | Snake_case (correct) |
| SemanticScholar | `referenceCount` | `reference_count` | Snake_case (correct) |

### 8.3 Type Coercion Issues

| Provider | Field | API Type | Schema Type | Issue |
|----------|-------|----------|-------------|-------|
| OpenAlex | `year` | `int` | `pd.Int64Dtype` | Nullable int handling |
| OpenAlex | `citation_count` | `int` | `pd.Int64Dtype` | Nullable int handling |
| SemanticScholar | `corpus_id` | `int` | `pd.Int64Dtype` | Nullable int handling |
| PubMed | `pmid` | `int` (XML) | `str` | String for cross-provider consistency |

---

## 9. Correction Prompts

### 9.1 ChEMBL Activity Pipeline Enhancement

**PROMPT 1: Add Missing ChEMBL Activity Fields**

The ChEMBL Activity pipeline currently extracts most fields from the ChEMBL REST API but is missing several important data quality and curation fields that could improve downstream analysis and data governance. After reviewing the ChEMBL API schema at `https://www.ebi.ac.uk/chembl/api/data/activity/schema`, I identified that the `data_validity_description` field provides human-readable explanations for data quality issues, complementing the existing `data_validity_comment` field which only provides coded values.

Additionally, the `manual_curation_flag` and `original_activity_id` fields are currently commented out in the schema at `src/bioetl/domain/schemas/chembl/activity.py` (lines 148-158). The `manual_curation_flag` indicates whether an activity record has been manually reviewed by ChEMBL curators, which is valuable for quality filtering in drug discovery pipelines. The `original_activity_id` provides traceability to the original source record when activities have been standardized or merged.

To implement these changes, you should:
1. Uncomment the `manual_curation_flag` and `original_activity_id` fields in the ActivitySchema
2. Add `data_validity_description` as a new optional string field
3. Update the ActivityTransformer at `src/bioetl/application/pipelines/chembl/activity_transformer.py` to extract these fields in the `_QUALITY_ANNOTATIONS` FieldGroup
4. Add corresponding fields to the PyArrow schema in `src/bioetl/infrastructure/schemas/silver.py`
5. Update tests in `tests/unit/domain/schemas/chembl/test_activity_schema.py`

The business value includes improved data quality tracking, better audit trails for curated data, and enhanced filtering capabilities for high-confidence bioactivity data in drug discovery applications.

---

### 9.2 PubChem Compound Pipeline Enhancement

**PROMPT 2: Add Missing PubChem 3D Molecular Descriptors**

The PubChem Compound pipeline at `src/bioetl/application/pipelines/pubchem/transformer.py` currently extracts most molecular properties from PubChem's PUG REST API but is missing several important 3D shape descriptors that are valuable for molecular modeling and virtual screening applications. Specifically, the pipeline does not extract the steric quadrupole moments (`XStericQuadrupole3D`, `YStericQuadrupole3D`, `ZStericQuadrupole3D`) which describe the 3D charge distribution shape of molecules, and the `FeatureCount3D` which provides the total count of pharmacophore features.

The PubChem API provides these fields when requesting the `/property/` endpoint with the appropriate property names. Currently, the transformer only handles basic 3D properties defined in `PubchemMoleculeSchema` at `src/bioetl/domain/schemas/pubchem/compound.py`, but the steric quadrupole descriptors are absent despite being available from the API.

Additionally, the `MonoisotopicMass` field, while similar to `ExactMass`, uses a different calculation method (most abundant isotope vs exact isotopic composition) and may be preferred in mass spectrometry applications. The pipeline currently only extracts `exact_mass` but should also capture `MonoisotopicMass` as a separate field.

To implement these enhancements:
1. Add `x_steric_quadrupole_3d`, `y_steric_quadrupole_3d`, `z_steric_quadrupole_3d` as nullable float fields in `PubchemMoleculeSchema`
2. Add `feature_count_3d` as a nullable integer field
3. Add `monoisotopic_mass` as a nullable float field
4. Update the transformer to extract these fields from the Bronze record
5. Update the PubChem adapter to request these additional properties from the API
6. Add validation checks for the quadrupole fields (can be negative) and feature count (must be non-negative)

These additions will enable more comprehensive molecular shape analysis for structure-activity relationship studies and improve compatibility with computational chemistry workflows that rely on 3D descriptors.

---

### 9.3 CrossRef Publication Pipeline Enhancement

**PROMPT 3: Extract Full Author and Reference Data from CrossRef**

The CrossRef Publication pipeline at `src/bioetl/application/pipelines/crossref/transformer.py` currently extracts author names but does not capture the full author structure provided by the CrossRef API, which includes ORCID identifiers, institutional affiliations, and author sequence information. This limitation significantly reduces the value of CrossRef data for author disambiguation, institutional analysis, and research collaboration studies.

The CrossRef API `/works` endpoint returns an `author` array where each author object contains: `given` (first name), `family` (last name), `ORCID` (persistent identifier), `affiliation` (array of institution objects), `sequence` (first/additional), and `authenticated-orcid` (boolean). Currently, the `extract_authors` function in `src/bioetl/application/pipelines/crossref/extractors.py` only extracts the name components and discards the ORCID and affiliation data.

Similarly, the `reference` field containing the full bibliography of cited works is not extracted. This field provides DOIs, article titles, authors, and other metadata for each reference, which is essential for citation network analysis and bibliometric studies. The CrossRef API provides this data under the `reference` array in work records.

To implement comprehensive author and reference extraction:
1. Update `extract_authors()` to return a structured dict including `given`, `family`, `orcid`, `sequence`, and `authenticated_orcid`
2. Create a new `extract_affiliations()` function to parse the nested affiliation structure
3. Add `author_orcids` as a JSON array field in the schema to store ORCID identifiers
4. Create `extract_references()` function to parse the reference array
5. Add `references` as a JSON field containing the serialized reference list
6. Update `PublicationSchema` at `src/bioetl/domain/schemas/crossref/work.py` to include these new fields
7. Consider PII implications for author data and apply appropriate hashing per RULES.md §5.4

This enhancement will enable robust author identification through ORCID matching, institutional affiliation analysis, and complete citation network construction from CrossRef data.

---

### 9.4 OpenAlex Publication Pipeline Enhancement

**PROMPT 4: Migrate from Deprecated Concepts to Topics System**

The OpenAlex Publication pipeline at `src/bioetl/application/pipelines/openalex/transformer.py` currently extracts the `concepts` field which OpenAlex has deprecated in favor of the new `topics` classification system introduced in 2024. The concepts system provided broad subject categorization, but the topics system offers more granular, hierarchical classification with better coverage and accuracy for scientific publications.

The transformer currently calls `extract_concepts(rec.get("concepts", []))` at line 153, but the OpenAlex API now recommends using `topics` which provides a four-level hierarchy: domain, field, subfield, and topic. Each topic object includes `id`, `display_name`, `score`, `subfield`, `field`, and `domain` properties that enable multi-resolution subject classification.

Additionally, the pipeline does not extract the `grants` field which OpenAlex added to provide funding information. This field contains an array of grant objects with `funder`, `funder_display_name`, and `award_id` properties that are valuable for research funding analysis and compliance reporting.

The `primary_topic` field, which identifies the single most relevant topic for a work, is also not extracted despite being a useful summary classification.

To migrate to the topics system and add grants:
1. Create `extract_topics()` function in `src/bioetl/application/pipelines/openalex/extractors.py` to parse the hierarchical topic structure
2. Add `extract_primary_topic()` to get the single most relevant topic
3. Create `extract_grants()` to parse funding information
4. Update `OpenAlexPublicationSchema` to include `topics`, `primary_topic`, and `grants` fields
5. Deprecate the `concepts` field with a migration path (keep for backward compatibility temporarily)
6. Update the transformer to extract both systems during transition period
7. Add documentation noting the deprecation timeline

This migration ensures the pipeline uses OpenAlex's current best practices for subject classification and captures funding metadata that is increasingly important for research analytics.

---

### 9.5 UniProt Protein Pipeline Enhancement

**PROMPT 5: Add Biochemical and Structural Cross-Reference Data**

The UniProt Protein pipeline at `src/bioetl/application/pipelines/uniprot/transformer.py` extracts comprehensive functional annotation data but is missing several biochemically important fields that UniProt provides. Specifically, the `cofactor` comments section describes essential metal ions and organic molecules required for protein function, which is critical for enzyme characterization and drug target analysis.

The `biophysicochemical_properties` comment type contains experimentally determined pH optima, temperature optima, kinetic parameters (Km, Vmax), and redox potential values. These quantitative properties are essential for protein engineering, biotechnology applications, and understanding enzyme behavior under different conditions.

Currently, the `CommentExtractor` class at `src/bioetl/application/pipelines/uniprot/extractors.py` extracts comments for `FUNCTION`, `ACTIVITY REGULATION`, `SUBUNIT`, `PATHWAY`, `DISEASE`, `SIMILARITY`, and `CAUTION` types, but does not handle `COFACTOR`, `BIOPHYSICOCHEMICAL PROPERTIES`, or `INDUCTION` comment types.

Additionally, the PDB cross-references which provide 3D structure availability are not extracted despite being valuable for structural biology applications. The current `CrossRefExtractor` only extracts GO, DrugBank, ChEMBL, and GuidetoPHARMACOLOGY references.

To add these biochemical and structural fields:
1. Add `extract_cofactors()` method to `CommentExtractor` to parse COFACTOR comments with chebi_id and name
2. Add `extract_biophysicochemical_properties()` for pH, temperature, kinetic data
3. Add `extract_induction()` for gene expression induction conditions
4. Extend `CrossRefExtractor.extract_xref_ids()` to handle PDB references
5. Add corresponding fields to `UniprotTargetSchema`: `cofactors`, `biophysicochemical_properties`, `induction`, `pdb_ids`
6. Update the transformer `_add_functional_annotations()` method to call new extractors
7. Serialize complex cofactor structures as JSON for the schema

These additions will significantly enhance the utility of UniProt data for enzyme characterization, structural biology research, and biotechnology applications where biochemical properties are essential selection criteria.

---

### 9.6 PubMed Publication Pipeline Enhancement

**PROMPT 6: Extract Complete Affiliation and Identifier Data from PubMed**

The PubMed Publication pipeline at `src/bioetl/application/pipelines/pubmed/transformer.py` currently extracts basic author information but does not fully capture the `AffiliationInfo` structure that MEDLINE provides, which includes institutional identifiers, email addresses (for correspondence), and structured affiliation components. This limitation affects the ability to perform institutional-level bibliometric analysis and author disambiguation.

The MEDLINE XML format provides `AffiliationInfo` elements within each `Author` element that can contain multiple `Affiliation` elements, each with a potential `Identifier` attribute linking to institutional databases like ROR (Research Organization Registry) or GRID. The current `AuthorExtractor.parse_affiliations()` at `src/bioetl/application/pipelines/pubmed/extractors.py` extracts affiliation text but discards identifier metadata.

Additionally, the pipeline does not extract the complete set of external identifiers available in PubMed records. The `ArticleIdList` in `PubmedData` can contain identifiers beyond DOI and PMC, including `pubmed-not-medline` status indicators, publisher-specific IDs, and mid (manuscript ID) values used in the PMC submission process.

The `ELocationID` elements provide additional electronic location identifiers including PII (Publisher Item Identifier) values that some publishers use for article tracking. These are currently not extracted despite being useful for publisher-specific data integration.

To implement comprehensive affiliation and identifier extraction:
1. Update `AuthorExtractor.parse_affiliations()` to extract `Identifier` attributes with source type
2. Create structured affiliation objects with `text`, `identifier`, and `identifier_source` fields
3. Add `parse_all_article_ids()` method to `IdentifierExtractor` for complete ID extraction
4. Add `pii`, `mid`, and `publisher_id` fields to `PubMedPublicationSchema`
5. Extract `ELocationID` elements and add corresponding schema fields
6. Update the transformer to call enhanced extractors
7. Consider PII implications for email addresses in affiliations and apply hashing

This enhancement will enable robust institutional analysis, improve author disambiguation through institutional identifiers, and provide complete cross-referencing capabilities with publisher databases.

---

### 9.7 SemanticScholar Publication Pipeline Enhancement

**PROMPT 7: Add Author Identifiers and Citation Context Data**

The Semantic Scholar Publication pipeline at `src/bioetl/application/pipelines/semanticscholar/transformer.py` extracts author names but does not capture the rich author metadata that the S2 API provides, including S2 author IDs, ORCID identifiers, DBLP keys, and h-index values. This information is essential for author-level analytics, disambiguation, and research impact assessment.

The S2 API returns an `authors` array where each author object contains: `authorId` (40-char hex S2 ID), `externalIds` (ORCID, DBLP, etc.), `name`, `aliases`, `url`, `hIndex`, and `citationCount`. The current `extract_authors()` function in `src/bioetl/application/pipelines/semanticscholar/extractors.py` only extracts the name field and discards this valuable metadata.

Additionally, the S2 API provides `contexts` when requesting citation or reference details, which are the actual sentences where a paper is cited. This citation context data is invaluable for understanding how research is used and for citation sentiment analysis. The current pipeline does not request or extract citation contexts.

The paper `embedding` field provides a dense vector representation of the paper's content that can be used for semantic similarity search and clustering. While storage of embeddings requires special consideration due to their size (768 dimensions), they are increasingly important for ML-powered literature discovery.

To implement author identifier and citation context extraction:
1. Update `extract_authors()` to return structured objects with `name`, `authorId`, `orcid`, `dblp_id`, `h_index`
2. Add `author_s2_ids` and `author_orcids` JSON array fields to the schema
3. Create `extract_citation_contexts()` function to parse context data when available
4. Add `citation_contexts` field for storing citing sentence excerpts
5. Consider adding `embedding` as a binary field or separate storage mechanism
6. Update the S2 adapter to request `authors.externalIds` and `authors.hIndex` in the fields parameter
7. Update `SemanticScholarPublicationSchema` at `src/bioetl/domain/schemas/semanticscholar/publication.py`

This enhancement will enable comprehensive author analytics, support citation context-aware literature reviews, and provide the foundation for semantic similarity features in the publication dataset.

---

## Appendix A: Complete Field Inventory

### ChEMBL Activity (56 fields)
```
activity_id, assay_chembl_id, molecule_chembl_id, target_chembl_id, document_chembl_id,
standard_relation, standard_value, standard_units, standard_type, standard_flag,
pchembl_value, data_validity_comment, activity_comment, potential_duplicate,
bao_endpoint, uo_units, qudt_units, src_id, record_id, type, relation, value,
units, text_value, standard_text_value, upper_value, standard_upper_value, toid,
ligand_efficiency_bei, ligand_efficiency_le, ligand_efficiency_lle, ligand_efficiency_sei,
action_type_action_type, action_type_description, action_type_parent_type,
canonical_smiles, molecule_pref_name, parent_molecule_chembl_id, target_pref_name,
target_organism, target_taxonomy_id, assay_type, assay_description,
assay_variant_accession, assay_variant_mutation, bao_format, bao_label,
document_journal, document_year, activity_properties,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### PubChem Compound (35 fields)
```
cid, canonical_smiles, isomeric_smiles, inchi, inchi_key, molecular_formula,
iupac_name, molecular_weight, exact_mass, xlogp, tpsa, complexity, charge,
heavy_atom_count, h_bond_donor_count, h_bond_acceptor_count, rotatable_bond_count,
atom_stereo_count, defined_atom_stereo_count, undefined_atom_stereo_count,
bond_stereo_count, defined_bond_stereo_count, undefined_bond_stereo_count,
isotope_atom_count, covalent_unit_count, volume_3d, conformer_count_3d,
feature_acceptor_count_3d, feature_donor_count_3d, feature_anion_count_3d,
feature_cation_count_3d, feature_ring_count_3d, feature_hydrophobe_count_3d,
effective_rotor_count_3d, conformer_rmsd_3d,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### UniProt Protein (53 fields)
```
accession, entry_name, entry_type, secondary_accessions, protein_name,
protein_short_names, protein_alternative_names, protein_ec_numbers, flag,
gene_primary, gene_synonyms, gene_orf_names, organism_scientific,
organism_common, taxonomy_id, lineage, protein_existence, annotation_score,
reviewed, sequence, sequence_length, sequence_mass, sequence_checksum,
sequence_modified, entry_version, entry_created, entry_modified,
function_comment, catalytic_activity, activity_regulation, subunit, pathway,
subcellular_location, tissue_specificity, alternative_products,
disease_involvement, pharmaceutical_use, similarity_comment, caution,
go_terms, drugbank_ids, chembl_ids, guidetopharmacology_ids, features,
keywords, cross_reference_count, feature_count, keyword_count,
publication_count, isoform_count,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### CrossRef Publication (28 fields)
```
doi, type, title, container_title, publisher, issn, isbn, volume, issue, page,
published_date, created_date, deposited_date, abstract, language, subject,
license_url, is_referenced_by_count, references_count, funder_names,
clinical_trial_numbers, update_policy, authors, affiliations,
_source, _lookup_method, _original_id, _dq_warn, _dq_error,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### OpenAlex Publication (32 fields)
```
openalex_id, doi, pmid, pmc_id, mag_id, title, abstract, authors, affiliations,
journal, issn, publisher, year, publication_date, doc_type, is_oa, oa_status,
citation_count, concepts, mesh, keywords, language, volume, issue, first_page,
last_page, fwci, referenced_works_count, is_retracted,
_source, _lookup_method, _original_id, _dq_warn, _dq_error,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### PubMed Publication (42 fields)
```
pmid, doi, pmc_id, title, vernacular_title, abstract, abstract_structured,
authors, affiliations, author_count, journal, journal_title, journal_abbrev,
journal_iso_abbrev, issn, journal_issn_type, nlm_unique_id, country,
volume, issue, pages, medline_pgn, first_page, last_page, year,
publication_year, pub_month, pub_day, publication_date, publication_status,
publication_type_list, publication_types, keywords, keyword_count,
mesh_terms, mesh_heading_count, chemicals, chemical_count, gene_symbols,
databanks, citation_subset, grant_count, reference_count, language,
date_completed, date_revised, accepted_date, received_date, revised_date,
epub_date, pub_date,
_source, _lookup_method, _original_id, _dq_warn, _dq_error,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

### SemanticScholar Publication (30 fields)
```
paper_id, doi, pmid, pmc_id, arxiv_id, dblp_id, corpus_id, title, abstract,
tldr, authors, affiliations, journal, volume, pages, first_page, last_page,
venue, year, publication_date, citation_count, reference_count,
influential_citation_count, is_oa, open_access_url, oa_status,
fields_of_study, publication_types,
_source, _lookup_method, _original_id, _dq_warn, _dq_error,
_entity_id, _content_hash, _run_id, _timestamp, _record_index
```

---

## Appendix B: Verification Commands

```bash
# Count fields in schemas
grep -c "Series\[" src/bioetl/domain/schemas/chembl/activity.py
grep -c "Series\[" src/bioetl/domain/schemas/pubchem/compound.py
grep -c "Series\[" src/bioetl/domain/schemas/uniprot/protein.py

# Find commented-out fields
grep -n "^    # " src/bioetl/domain/schemas/chembl/*.py

# Check transformer field extraction
grep -o '"[a-z_]*":' src/bioetl/application/pipelines/*/transformer.py | sort -u

# Verify PyArrow schema alignment
grep "pa.field" src/bioetl/infrastructure/schemas/silver.py | wc -l
```

---

**Report End**
