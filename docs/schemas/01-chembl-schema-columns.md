01 Chembl Schema Columns
========================

Canonical column order for ChEMBL outputs. Lists mirror the `OUTPUT_COLUMN_ORDER`
constants in `src/bioetl/domain/schemas/chembl/*`. Business columns go first, then
the generated metadata columns `hash_row`, `hash_business_key`, `index`,
`database_version`, `acquisition_timestamp`.

## Activity

`action_type`, `activity_comment`, `activity_id`, `activity_properties`,
`assay_chembl_id`, `assay_description`, `assay_type`, `assay_variant_accession`,
`assay_variant_mutation`, `bao_endpoint`, `bao_format`, `bao_label`,
`canonical_smiles`, `data_validity_comment`, `data_validity_description`,
`document_chembl_id`, `document_journal`, `document_year`, `ligand_efficiency`,
`molecule_chembl_id`, `molecule_pref_name`, `parent_molecule_chembl_id`,
`pchembl_value`, `potential_duplicate`, `qudt_units`, `record_id`, `relation`,
`src_id`, `standard_flag`, `standard_relation`, `standard_text_value`,
`standard_type`, `standard_units`, `standard_upper_value`, `standard_value`,
`target_chembl_id`, `target_organism`, `target_pref_name`, `target_tax_id`,
`text_value`, `toid`, `type`, `units`, `uo_units`, `upper_value`, `value`,
`hash_row`, `hash_business_key`, `index`, `database_version`, `acquisition_timestamp`.

## Assay

`aidx`, `assay_category`, `assay_cell_type`, `assay_chembl_id`,
`assay_classifications`, `assay_group`, `assay_organism`, `assay_parameters`,
`assay_strain`, `assay_subcellular_fraction`, `assay_tax_id`, `assay_test_type`,
`assay_tissue`, `assay_type`, `assay_type_description`, `bao_format`, `bao_label`,
`cell_chembl_id`, `confidence_description`, `confidence_score`, `description`,
`document_chembl_id`, `relationship_description`, `relationship_type`, `score`,
`src_assay_id`, `src_id`, `target_chembl_id`, `tissue_chembl_id`,
`variant_sequence`, `hash_row`, `hash_business_key`, `index`, `database_version`,
`acquisition_timestamp`.

## Molecule

`atc_classifications`, `availability_type`, `black_box_warning`, `chemical_probe`,
`chirality`, `cross_references`, `dosed_ingredient`, `first_approval`,
`first_in_class`, `helm_notation`, `inorganic_flag`, `max_phase`,
`molecule_chembl_id`, `molecule_hierarchy`, `molecule_properties`,
`molecule_structures`, `molecule_synonyms`, `molecule_type`, `natural_product`,
`oral`, `orphan`, `parenteral`, `polymer_flag`, `pref_name`, `prodrug`,
`structure_type`, `therapeutic_flag`, `topical`, `usan_stem`,
`usan_stem_definition`, `usan_substem`, `usan_year`, `veterinary`,
`withdrawn_flag`, `hash_row`, `hash_business_key`, `index`, `database_version`,
`acquisition_timestamp`.

## Publication

`abstract`, `authors`, `chembl_release`, `contact`, `doc_type`,
`document_chembl_id`, `doi`, `doi_chembl`, `first_page`, `issue`, `journal`,
`journal_full_title`, `last_page`, `patent_id`, `pubmed_id`, `score`, `src_id`,
`title`, `volume`, `year`, `hash_row`, `hash_business_key`, `index`,
`database_version`, `acquisition_timestamp`.

## Target

`target_chembl_id`, `pref_name`, `score`, `organism`, `target_type`, `tax_id`,
`species_group_flag`, `target_components`, `cross_references`, `uniprot_id`,
`hash_row`, `hash_business_key`, `index`, `database_version`, `acquisition_timestamp`.

## Cell

`cell_chembl_id`, `cell_name`, `cell_source_organism`, `cell_type`,
`cell_description`, `hash_row`, `hash_business_key`, `index`, `database_version`,
`acquisition_timestamp`.

## Tissue

`tissue_chembl_id`, `tissue_name`, `tissue_source_organism`, `tissue_description`,
`tissue_type`, `hash_row`, `hash_business_key`, `index`, `database_version`,
`acquisition_timestamp`.

