# Reference Identifier Families

Scope: governed non-ChEMBL identifier families canonicalized by
`src/bioetl/domain/normalization/reference_ids.py`.

This inventory is the compact human-facing companion to the generated
normalization matrix. It documents which identifier families are governed by the
shared registry, how they are stored, and where DQ is expected to enforce
shape versus where profile/domain canonicalization is the primary guardrail.

Related:
- `src/bioetl/domain/normalization/reference_ids.py`
- `src/bioetl/domain/normalization/_reference_id_registry.py`
- `docs/05-engineering/normalization_plan_P0_P6.md`

DQ alignment:
- scalar identifiers like `doi`, `pmid`, `pmcid`, `mesh`, `ncbi_taxonomy`,
  `paper_id`, `openalex_id`, and `uniprot_accession` may also have direct
  pattern/range validation in entity configs and domain schemas
- JSON-array/object identifier families use `domain.normalization.reference_ids`
  as the canonical vocabulary seam; DQ generally validates the container shape,
  while profile/domain normalization canonicalizes the embedded identifiers

| Family | Storage | Collection semantics | Canonical form | Example fields |
| --- | --- | --- | --- | --- |
| `orcid` | string | set-like | `0000-0000-0000-0000` | `crossref_publication.author_orcids`, `openalex_publication.author_orcids`, `pubmed_publication.author_orcids`, `semanticscholar_publication.author_orcids` |
| `issn` | string | set-like | `1234-567X` | `crossref_publication.issn`, `crossref_publication.issn_list`, `openalex_publication.issn`, `pubmed_publication.issn` |
| `ror` | string | set-like | `https://ror.org/...` | `openalex_publication.ror_ids` |
| `openalex_author` | string | set-like | `A123` | `openalex_publication.author_openalex_ids` |
| `openalex_institution` | string | set-like | `I123` | `openalex_publication.institution_ids` |
| `openalex_topic` | json object or array | set-like | `T123` inside canonical JSON | `openalex_publication.primary_topic`, `openalex_publication.subject_topics` |
| `openalex_work` | string | scalar | `W123` | `openalex_publication.openalex_id` |
| `semantic_scholar_author` | string | set-like | lowercase 40-char hex | `semanticscholar_publication.author_s2_ids` |
| `semantic_scholar_paper` | string | scalar or set-like | lowercase 40-char hex | `semanticscholar_publication.paper_id` |
| `semantic_scholar_corpus` | numeric scalar | scalar | numeric corpusId | `semanticscholar_publication.corpus_id` |
| `ncbi_taxonomy` | numeric scalar | scalar | numeric taxonomy id | `chembl_activity.target_tax_id`, `chembl_assay.tax_id`, `chembl_target.tax_id` |
| `uniprot_accession` | string | scalar or set-like | uppercase accession | `uniprot_idmapping.uniprot_accession`, `uniprot_idmapping.all_mappings`, `uniprot_protein.secondary_accessions` |
| `go` | json array | set-like | `GO:0000000` | `uniprot_protein.go_terms`, `uniprot_protein.cellular_component`, `uniprot_protein.molecular_function` |
| `interpro` | json array | set-like | `IPR000000` | `uniprot_protein.interpro_xrefs` |
| `pfam` | json array | set-like | `PF00000` | `uniprot_protein.pfam_xrefs` |
| `reactome` | json array | set-like | `R-HSA-123456` | `uniprot_protein.reactome_xrefs` |
| `pdb` | json array | set-like | uppercase 4-char ID | `uniprot_protein.pdb_xrefs` |
| `chembl` | string | scalar or set-like | `CHEMBL123` | `uniprot_idmapping.target_id`, `uniprot_protein.chembl_ids` |
| `doi` | string | scalar | canonical DOI token | `crossref_publication.doi`, `openalex_publication.doi`, `pubmed_publication.doi`, `semanticscholar_publication.doi` |
| `pmid` | numeric string | scalar | canonical PubMed integer string | `chembl_publication.pubmed_id`, `pubmed_publication.pmid` |
| `pmcid` | string | scalar | `PMC1234567` | `pubmed_publication.pmcid` |
| `mesh` | string | scalar | `D000001` | `pubmed_publication.mesh_primary`, `pubmed_publication.mesh_terms` |
| `drugbank` | string | set-like | `DB00001` | `uniprot_protein.drugbank_ids` |
