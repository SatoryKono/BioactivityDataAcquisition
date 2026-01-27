# Data Providers Documentation

This directory contains documentation for each data source provider integrated with BioETL.

## Supported Providers

| Provider | Entities | Status |
|----------|----------|--------|
| [ChEMBL](chembl/) | Activity, Assay, Molecule, Target, etc. | Active |
| [PubChem](pubchem/compound.md) | Compound | Active |
| [UniProt](uniprot/idmapping.md) | ID Mapping | Active |
| [PubMed](pubmed/publication.md) | Publication | Active |
| [CrossRef](crossref/publication.md) | Publication | Active |
| [OpenAlex](openalex/publication.md) | Publication | Active |
| [SemanticScholar](semanticscholar/publication.md) | Publication | Active |

## ChEMBL Entities

ChEMBL provides comprehensive bioactivity data with multiple entity types:

| Entity | Document | Pipeline Status |
|--------|----------|-----------------|
| [Activity](chembl/activity.md) | Entity schema and fields | ✅ Active |
| [Assay](chembl/assay.md) | Bioassay definitions | ✅ Active |
| [Molecule](chembl/molecule.md) | Chemical compounds | ✅ Active |
| [Target](chembl/target.md) | Biological targets | ✅ Active |
| [Assay Parameters](chembl/assay-parameters.md) | Assay parameter definitions | Planned |
| [Cell Line](chembl/cell-line.md) | Cell line data | Planned |
| [Compound Record](chembl/compound-record.md) | Compound records | Planned |
| [Publication](chembl/publication.md) | Literature references | ✅ Active |
| [Publication Similarity](chembl/publication-similarity.md) | Publication similarity | ✅ Active |
| [Publication Term](chembl/publication-term.md) | Publication terms | ✅ Active |
| [Protein Class](chembl/protein-class.md) | Protein classification | Planned |
| [Target Component](chembl/target-component.md) | Target components | Planned |

## Provider Configuration

Pipeline configurations for providers are in `configs/pipelines/{provider}/`:

```
configs/pipelines/
├── chembl/           # ChEMBL pipeline configs
├── pubchem/          # PubChem configs
├── uniprot/          # UniProt configs
├── pubmed/           # PubMed configs
├── crossref/         # CrossRef configs
├── openalex/         # OpenAlex configs
└── semanticscholar/  # SemanticScholar configs
```

## Related Documentation

- [RULES.md](../RULES.md) Appendix A — Provider rate limits and libraries
- [03-guides/add-new-source.md](../03-guides/add-new-source.md) — Adding new providers
- [02-architecture/03-infrastructure-layer.md](../02-architecture/03-infrastructure-layer.md) — Adapter architecture
