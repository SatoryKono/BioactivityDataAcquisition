# Config Discrepancies Report

Total configs: 27
Total unique parameters: 525
Actionable inconsistent parameters: 0
Sanctioned partial variance parameters: 107
Raw partial parameter count: 107

## Actionable Drift Parameters

No unsanctioned config drift detected.

## Sanctioned Partial Variance Parameters

These parameters are intentionally partial across governed config families and remain tracked as sanctioned variance rather than actionable drift.


### entity_effective

- `filters.extraction_params.assay_type__in` (2/22): entity/chembl/activity, entity/chembl/assay
- `filters.extraction_params.confidence_score__gte` (1/22): entity/chembl/assay
- `filters.extraction_params.data_validity_comment__isnull` (1/22): entity/chembl/activity
- `filters.extraction_params.doc_type` (2/22): entity/chembl/publication, entity/chembl/publication_term
- `filters.extraction_params.inorganic_flag` (1/22): entity/chembl/molecule
- `filters.extraction_params.molecule_type` (1/22): entity/chembl/molecule
- `filters.extraction_params.organism__isnull` (1/22): entity/chembl/target
- `filters.extraction_params.pchembl_value__isnull` (1/22): entity/chembl/activity
- `filters.extraction_params.potential_duplicate` (1/22): entity/chembl/activity
- `filters.extraction_params.relationship_type` (1/22): entity/chembl/assay
- `filters.extraction_params.standard_flag` (1/22): entity/chembl/activity
- `filters.extraction_params.standard_relation` (1/22): entity/chembl/activity
- `filters.extraction_params.standard_type__in` (1/22): entity/chembl/activity
- `filters.extraction_params.standard_units` (1/22): entity/chembl/activity
- `filters.extraction_params.structure_type` (1/22): entity/chembl/molecule
- `filters.extraction_params.target_chembl_id__isnull` (1/22): entity/chembl/assay
- `filters.extraction_params.target_tax_id__isnull` (1/22): entity/chembl/activity
- `filters.extraction_params.target_type` (1/22): entity/chembl/target
- `filters.extraction_params.tax_id__isnull` (1/22): entity/chembl/target
- `filters.extraction_params.year__gte` (2/22): entity/chembl/publication, entity/chembl/publication_term
- `filters.extraction_params.year__lte` (2/22): entity/chembl/publication, entity/chembl/publication_term
- `filters.gold_filters.columns.assay_strain` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.assay_strain.operator` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.assay_test_type` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.assay_test_type.operator` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.assay_test_type.values` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.assay_type` (2/22): entity/chembl/activity, entity/chembl/assay
- `filters.gold_filters.columns.bao_format` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.bao_format.operator` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.bao_format.values` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.component_type` (1/22): entity/chembl/target_component
- `filters.gold_filters.columns.confidence_score` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.inorganic_flag` (1/22): entity/chembl/molecule
- `filters.gold_filters.columns.molecule_type` (1/22): entity/chembl/molecule
- `filters.gold_filters.columns.potential_duplicate` (2/22): entity/chembl/activity, entity/chembl/molecule
- `filters.gold_filters.columns.publication_type` (1/22): entity/chembl/publication
- `filters.gold_filters.columns.reviewed` (1/22): entity/uniprot/protein
- `filters.gold_filters.columns.src_id` (1/22): entity/chembl/assay
- `filters.gold_filters.columns.standard_relation` (1/22): entity/chembl/activity
- `filters.gold_filters.columns.standard_type` (1/22): entity/chembl/activity
- `filters.gold_filters.columns.standard_units` (1/22): entity/chembl/activity
- `filters.gold_filters.columns.structure_type` (1/22): entity/chembl/molecule
- `filters.gold_filters.columns.target_type` (1/22): entity/chembl/target
- `filters.gold_filters.columns.term_type` (1/22): entity/chembl/publication_term
- `filters.gold_filters.list_contains.component_types` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_contains.component_types.mode` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_contains.component_types.values` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_lengths.component_accessions` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_lengths.component_accessions.max` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_lengths.component_accessions.min` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_lengths.component_ids` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.list_lengths.component_ids.min` (2/22): entity/chembl/target, entity/chembl/target_component
- `filters.gold_filters.ranges.max_tani` (1/22): entity/chembl/publication_similarity
- `filters.gold_filters.ranges.max_tani.include_min` (1/22): entity/chembl/publication_similarity
- `filters.gold_filters.ranges.max_tani.min` (1/22): entity/chembl/publication_similarity
- `filters.gold_filters.ranges.publication_year` (4/22): entity/chembl/activity, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/target_component
- `filters.gold_filters.ranges.publication_year.max` (4/22): entity/chembl/activity, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/target_component
- `filters.gold_filters.ranges.publication_year.min` (4/22): entity/chembl/activity, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/target_component
- `filters.gold_filters.ranges.standard_value` (1/22): entity/chembl/activity
- `filters.gold_filters.ranges.standard_value.include_min` (1/22): entity/chembl/activity
- `filters.gold_filters.ranges.standard_value.min` (1/22): entity/chembl/activity
- `filters.metadata.publication_filter_policy` (21/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/cell_line, entity/chembl/compound_record, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/target_protein_classification, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.metadata.publication_filter_policy.description` (21/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/cell_line, entity/chembl/compound_record, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/target_protein_classification, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.metadata.publication_filter_policy.scope` (21/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/cell_line, entity/chembl/compound_record, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/target_protein_classification, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.metadata.target_filter_policy` (1/22): entity/chembl/target
- `filters.metadata.target_filter_policy.description` (1/22): entity/chembl/target
- `filters.metadata.target_filter_policy.scope` (1/22): entity/chembl/target
- `filters.silver_filters.columns.assay_type` (2/22): entity/chembl/activity, entity/chembl/assay
- `filters.silver_filters.columns.inorganic_flag` (1/22): entity/chembl/molecule
- `filters.silver_filters.columns.molecule_type` (1/22): entity/chembl/molecule
- `filters.silver_filters.columns.potential_duplicate` (2/22): entity/chembl/activity, entity/chembl/molecule
- `filters.silver_filters.columns.publication_type` (1/22): entity/chembl/publication
- `filters.silver_filters.columns.relationship_type` (1/22): entity/chembl/assay
- `filters.silver_filters.columns.src_id` (1/22): entity/chembl/assay
- `filters.silver_filters.columns.standard_relation` (1/22): entity/chembl/activity
- `filters.silver_filters.columns.standard_type` (1/22): entity/chembl/activity
- `filters.silver_filters.columns.standard_units` (1/22): entity/chembl/activity
- `filters.silver_filters.columns.structure_type` (1/22): entity/chembl/molecule
- `filters.silver_filters.columns.target_type` (1/22): entity/chembl/target
- `filters.silver_filters.columns.term_type` (1/22): entity/chembl/publication_term
- `filters.silver_filters.ranges.activity_id` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.activity_id.max` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.activity_id.min` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.confidence_score` (1/22): entity/chembl/assay
- `filters.silver_filters.ranges.confidence_score.max` (1/22): entity/chembl/assay
- `filters.silver_filters.ranges.confidence_score.min` (1/22): entity/chembl/assay
- `filters.silver_filters.ranges.pchembl_value` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.pchembl_value.max` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.pchembl_value.min` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.publication_year` (18/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.silver_filters.ranges.publication_year.max` (18/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.silver_filters.ranges.publication_year.min` (18/22): entity/chembl/activity, entity/chembl/assay, entity/chembl/assay_parameters, entity/chembl/molecule, entity/chembl/protein_class, entity/chembl/publication, entity/chembl/publication_similarity, entity/chembl/publication_term, entity/chembl/subcellular_fraction, entity/chembl/target_component, entity/chembl/tissue, entity/crossref/publication, entity/openalex/publication, entity/pubchem/compound, entity/pubmed/publication, entity/semanticscholar/publication, entity/uniprot/idmapping, entity/uniprot/protein
- `filters.silver_filters.ranges.standard_value` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.standard_value.include_min` (1/22): entity/chembl/activity
- `filters.silver_filters.ranges.standard_value.min` (1/22): entity/chembl/activity
- `pipeline.field_policy.therapeutic_flag` (1/22): entity/chembl/molecule
- `pipeline.field_policy.therapeutic_flag.boolean_false_values` (1/22): entity/chembl/molecule
- `pipeline.field_policy.therapeutic_flag.boolean_true_values` (1/22): entity/chembl/molecule
- `pipeline.page_size_override` (1/22): entity/chembl/publication
- `pipeline.source.api` (2/22): entity/uniprot/idmapping, entity/uniprot/protein
- `pipeline.source.api.base_url` (2/22): entity/uniprot/idmapping, entity/uniprot/protein
- `pipeline.source.api.from_db` (2/22): entity/uniprot/idmapping, entity/uniprot/protein
- `pipeline.source.api.to_db` (2/22): entity/uniprot/idmapping, entity/uniprot/protein

### composite_runtime

- `composite.merge.target_protein_classification_projection` (1/5): composite/target
- `composite.merge.target_protein_classification_projection.include_protein_classifications` (1/5): composite/target
- `composite.merge.target_protein_classification_projection.levels` (1/5): composite/target
- `composite.merge.target_protein_classification_projection.source_prefix` (1/5): composite/target

## Interpretation

- CI should fail on actionable drift.
- Sanctioned partial variance remains inventory debt, not a merge blocker, while its governance contract stays current.