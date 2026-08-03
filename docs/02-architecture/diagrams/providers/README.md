______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Provider Data Flow Diagrams

**Issue:** #6545 · **Policy:** ADR-040

Each provider has four flowcharts:

1. API integration
2. Data transformation
3. Medallion layers
4. Error handling

| Provider | Directory |
| --- | --- |
| ChEMBL | [chembl/](chembl/) |
| PubChem | [pubchem/](pubchem/) |
| UniProt | [uniprot/](uniprot/) |
| PubMed | [pubmed/](pubmed/) |
| CrossRef | [crossref/](crossref/) |
| OpenAlex | [openalex/](openalex/) |
| Semantic Scholar | [semanticscholar/](semanticscholar/) |

Provider-specific mapping details live under `docs/04-reference/pipelines/**` and
normalization overviews — diagrams stay intentionally compact.
