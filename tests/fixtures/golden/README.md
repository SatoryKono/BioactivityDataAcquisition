# Golden Fixture Registry

This directory stores the bounded representative golden-master baseline declared
in `configs/quality/test_matrix.yaml` under
`fixture_governance.golden_master_registry`.

Current enforced provider baseline:

- `chembl`: `chembl_activity`, `chembl_molecule`, `chembl_publication_term`
- `crossref`: `crossref_publication`
- `openalex`: `openalex_publication`
- `pubchem`: `pubchem_compound`
- `pubmed`: `pubmed_publication`
- `semanticscholar`: `semanticscholar_publication`
- `uniprot`: `uniprot_protein`, `uniprot_idmapping`

Governance rules:

- Update snapshots only through `UPDATE_SNAPSHOTS=1` review flows.
- Add or remove representative pipelines only by changing the matrix registry
  and the matching architecture tests.
- Treat this baseline as representative, not exhaustive: it is a blocking
  policy surface for stable configuration-to-domain regression checks.
