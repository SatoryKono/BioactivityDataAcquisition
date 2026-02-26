# JSON Field Typing Inventory (Bronze -> Silver -> Gold)

Scope: inferred Bronze CSV samples + Silver Pandera + Silver PyArrow + Gold contracts.

| Field | Bronze inferred | Silver Pandera | Silver PyArrow | Gold contract |
| --- | --- | --- | --- | --- |
| `_ingestion_ts` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `_lookup_method` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `_original_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `_run_id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `_run_type` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `_source` | `unknown` (nullable) | — | `string` (nullable) | `str` (not-null) |
| `_source_batch_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `abstract` | `null` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `accession` | `null|string` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `acetylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `action_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `action_type_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `action_type_parent_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `active_sites` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity_comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity_id` | `integer` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `activity_properties` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `activity_regulation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `affiliation_list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `affiliation_structured` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `aidx` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `all_mappings` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `alternative_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `alternative_products` | `unknown` (nullable) | `str` (nullable) | — | — |
| `assay_category` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_cell_type` | `integer|null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_group` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `assay_organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_parameters` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_pref_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_strain` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_subcellular_fraction` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_test_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_tissue` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_type_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_variant_accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `assay_variant_mutation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `atc_classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_details` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_h_indices` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_keys` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_openalex_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_orcids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `author_s2_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `authors` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `authors_with_affiliations` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao_endpoint` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao_format` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `bao_label` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `binding_sites` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `biophysicochemical_properties` | `unknown` (nullable) | `str` (nullable) | — | — |
| `canonical_smiles` | `array|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `catalytic_activity` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `caution` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cell_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell_id` | `unknown` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `cell_name` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `cell_source_organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell_source_tissue` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cell_type` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cellosaurus_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cellular_component` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `chembl_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `chembl_release` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `chemicals` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `citation_contexts` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `citation_subset` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cl_lincs_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `clo_id` | `unknown` (nullable) | `str` (nullable) | — | — |
| `cofactors` | `unknown` (nullable) | `str` (nullable) | — | — |
| `comments` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_accessions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_descriptions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_relationships` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `component_types` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `compound_key` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `compound_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `confidence_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `content_domain_domains` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `content_hash` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `country` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `creation_date` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `cross_references` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `data_validity_comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `data_validity_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `databanks` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `date_completed` | `unknown` (nullable) | `datetime64[ns]` (nullable) | `string` (nullable) | `str` (nullable) |
| `date_revised` | `unknown` (nullable) | `datetime64[ns]` (nullable) | `string` (nullable) | `str` (nullable) |
| `dblp_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `definition` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `description` | `array|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `disease_involvement` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `disulfide_bond` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `doi` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `domains` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `drugbank_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `efo_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `entity_id` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `entry_name` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (nullable) |
| `entry_type` | `unknown` (nullable) | `str` (nullable) | — | — |
| `features_json` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `flag` | `unknown` (nullable) | `str` (nullable) | — | — |
| `function_comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene_names` | `unknown` (nullable) | — | `list<item: string>` (nullable) | `str` (nullable) |
| `gene_orf_names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `gene_primary` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene_symbols` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `gene_synonyms` | `unknown` (nullable) | `str` (nullable) | — | — |
| `genus` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `glycosylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `go_terms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `grants` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `guidetopharmacology_ids` | `unknown` (nullable) | `str` (nullable) | — | — |
| `helm_notation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy_active_chembl_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy_child_chembl_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `hierarchy_parent_chembl_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `inchi` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `inchi_key` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `induction` | `unknown` (nullable) | `str` (nullable) | — | — |
| `institution_country_codes` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `institution_ids` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `interpro_xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `intramembrane` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `isoform_ids` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `isoform_names` | `integer|null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `isoform_synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `isomeric_smiles` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn_electronic` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn_list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issn_print` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `issue` | `integer|null` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `iupac_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal` | `null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal_iso_abbrev` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal_issn_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `journal_name_short` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `keywords` | `unknown` (nullable) | `str` (nullable) | — | — |
| `language` | `unknown` (nullable) | `str` (nullable) | — | — |
| `license_url` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `lineage` | `unknown` (nullable) | `str` (nullable) | — | — |
| `lipidation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `logp_method` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mag_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mapping_status` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `medline_pgn` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mesh_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `mid` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `modified_residue` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecular_formula` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecular_function` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_hierarchy` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_id` | `unknown` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `molecule_pref_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_properties` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_species` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_structures` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `molecule_type` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `nlm_unique_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `oa_status` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `open_access_url` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `openalex_id` | `unknown` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `organism` | `string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `organism_class` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `organism_common` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `organism_scientific` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page_first` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page_last` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `page_range` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `paper_id` | `unknown` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `parent_molecule_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pathway` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pdb_xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pfam_xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pharmaceutical_use` | `unknown` (nullable) | `str` (nullable) | — | — |
| `phosphorylation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `phylum` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pii` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pipeline_stages` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pmc_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pmid` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pref_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `primary_topic` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `propeptide` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_alternative_names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `protein_class_desc` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_classification_ids` | `integer|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_classifications` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_ec_numbers` | `unknown` (nullable) | `str` (nullable) | — | — |
| `protein_existence` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `protein_short_names` | `unknown` (nullable) | `str` (nullable) | — | — |
| `pub_date` | `unknown` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `publication_class` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_date` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_doi` | `unknown` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `publication_id` | `string` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `publication_pmc_id` | `unknown` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `publication_pmid` | `unknown` (nullable) | — | `string` (nullable) | `str` (nullable) |
| `publication_status` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_subclass` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_type_list` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_type_unified` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publication_types` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published_online` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `published_print` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publisher` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `publisher_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pubmed_id1` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `pubmed_id2` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `qualifier` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `qudt_units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `reaction_ec_numbers` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `reactions` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `reactome_xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `references` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relationship_description` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `relationship_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `ro3_pass` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `ror_ids` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `secondary_accessions` | `unknown` (nullable) | `str` (nullable) | — | — |
| `sequence` | `unknown` (nullable) | `str` (not-null) | — | — |
| `sequence_checksum` | `unknown` (nullable) | `str` (nullable) | — | — |
| `short_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `signal_peptide` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `similarity_comment` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `src_assay_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `src_compound_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard_inchi` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard_relation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard_text_value` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `standard_units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `structure_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subcellular_location` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subject_fields` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subject_keywords` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `subject_mesh` | `unknown` (nullable) | `str` (nullable) | `list<item: string>` (nullable) | `str` (nullable) |
| `subject_topics` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `subunit` | `unknown` (nullable) | `str` (nullable) | — | — |
| `superkingdom` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_component_synonyms` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_component_xrefs` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_components` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_id` | `unknown` (nullable) | `str` (not-null) | `string` (not-null) | `str` (not-null) |
| `target_organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_pref_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `target_type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `term` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `term_type` | `unknown` (nullable) | `str` (not-null) | `string` (nullable) | `str` (not-null) |
| `text_value` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tissue_id` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tissue_specificity` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `title` | `array|null|string` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `tldr` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `topology` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `transmembrane` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `type` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (not-null) |
| `ubiquitination` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `uniprot_accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `uniprot_entry_name` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `uo_units` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan_stem` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan_stem_definition` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `usan_substem` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_accession` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_isoform` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_mutation` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_organism` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_sequence` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `variant_sequence_json` | `unknown` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
| `volume` | `integer|null` (nullable) | `str` (nullable) | `string` (nullable) | `str` (nullable) |
