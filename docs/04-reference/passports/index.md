# Pipeline and workflow passports

Generated, evidence-backed documentation projections.

## Governance

- [Pipeline passport projection guide](pipeline-passport-guide.md)
- [ADR-054: passport documentation projections](../../02-architecture/decisions/ADR-054-passport-documentation-projections.md)
- [ADR-055: workflow reconciliation ownership](../../02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md)
- [Pipeline passport schema](schemas/pipeline-passport.schema.json)
- [Workflow passport schema](schemas/workflow-passport.schema.json)
- [Manual metadata schema](schemas/manual-passport-metadata.schema.json)
- [Normalized duplication report](duplication-report.json)

- Owner: `BioETL Team`; review cadence: each executable/config change and release.
- Check: `python -m scripts.docs passports check`.
- Reviewed update: `python -m scripts.docs passports generate`.
- Generated facts are read-only projections; manual sidecars cannot override them.
- Diagram dataflow passports are compatibility companions and link back here.

## Pipelines

- [composite_activity](pipelines/composite-activity.md)
- [composite_assay](pipelines/composite-assay.md)
- [composite_molecule](pipelines/composite-molecule.md)
- [composite_publication](pipelines/composite-publication.md)
- [composite_target](pipelines/composite-target.md)
- [chembl_activity](pipelines/chembl-activity.md)
- [chembl_assay](pipelines/chembl-assay.md)
- [chembl_assay_parameters](pipelines/chembl-assay-parameters.md)
- [chembl_cell_line](pipelines/chembl-cell-line.md)
- [chembl_compound_record](pipelines/chembl-compound-record.md)
- [chembl_molecule](pipelines/chembl-molecule.md)
- [chembl_protein_class](pipelines/chembl-protein-class.md)
- [chembl_publication](pipelines/chembl-publication.md)
- [chembl_publication_similarity](pipelines/chembl-publication-similarity.md)
- [chembl_publication_term](pipelines/chembl-publication-term.md)
- [chembl_subcellular_fraction](pipelines/chembl-subcellular-fraction.md)
- [chembl_target](pipelines/chembl-target.md)
- [chembl_target_component](pipelines/chembl-target-component.md)
- [chembl_target_protein_classification](pipelines/chembl-target-protein-classification.md)
- [chembl_tissue](pipelines/chembl-tissue.md)
- [crossref_publication](pipelines/crossref-publication.md)
- [openalex_publication](pipelines/openalex-publication.md)
- [pubchem_compound](pipelines/pubchem-compound.md)
- [pubmed_publication](pipelines/pubmed-publication.md)
- [semanticscholar_publication](pipelines/semanticscholar-publication.md)
- [uniprot_idmapping](pipelines/uniprot-idmapping.md)
- [uniprot_protein](pipelines/uniprot-protein.md)

## Workflows

- [chembl_activity](workflows/chembl-activity.md)
- [chembl_assay](workflows/chembl-assay.md)
- [chembl_assay_parameters](workflows/chembl-assay-parameters.md)
- [chembl_baseline](workflows/chembl-baseline.md)
- [chembl_cell_line](workflows/chembl-cell-line.md)
- [chembl_compound_record](workflows/chembl-compound-record.md)
- [chembl_core](workflows/chembl-core.md)
- [chembl_molecule](workflows/chembl-molecule.md)
- [chembl_protein_class](workflows/chembl-protein-class.md)
- [chembl_publication](workflows/chembl-publication.md)
- [chembl_publication_similarity](workflows/chembl-publication-similarity.md)
- [chembl_publication_term](workflows/chembl-publication-term.md)
- [chembl_reference_pack](workflows/chembl-reference-pack.md)
- [chembl_subcellular_fraction](workflows/chembl-subcellular-fraction.md)
- [chembl_target](workflows/chembl-target.md)
- [chembl_target_component](workflows/chembl-target-component.md)
- [chembl_target_protein_classification](workflows/chembl-target-protein-classification.md)
- [chembl_tissue](workflows/chembl-tissue.md)
- [crossref_publication](workflows/crossref-publication.md)
- [openalex_publication](workflows/openalex-publication.md)
- [pubchem_compound](workflows/pubchem-compound.md)
- [publication_provider_pack](workflows/publication-provider-pack.md)
- [pubmed_publication](workflows/pubmed-publication.md)
- [semanticscholar_publication](workflows/semanticscholar-publication.md)
- [uniprot_idmapping](workflows/uniprot-idmapping.md)
- [uniprot_protein](workflows/uniprot-protein.md)
- [uniprot_support_pack](workflows/uniprot-support-pack.md)
