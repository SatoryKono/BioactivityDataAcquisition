______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# Data Providers Documentation

This directory contains documentation for each data source provider integrated with BioETL.

## Supported Providers

| Provider                                          | Entities                                                                | Status |
| ------------------------------------------------- | ----------------------------------------------------------------------- | ------ |
| [ChEMBL](chembl/activity.md)                      | Activity, Assay, Molecule, Target, Publication, plus auxiliary entities | Active |
| [PubChem](pubchem/compound.md)                    | Compound                                                                | Active |
| [UniProt](uniprot/protein.md)                     | Protein, ID Mapping                                                     | Active |
| [PubMed](pubmed/publication.md)                   | Publication                                                             | Active |
| [CrossRef](crossref/publication.md)               | Publication                                                             | Active |
| [OpenAlex](openalex/publication.md)               | Publication                                                             | Active |
| [SemanticScholar](semanticscholar/publication.md) | Publication                                                             | Active |

## ChEMBL Entities

ChEMBL provides comprehensive bioactivity data with multiple entity types:

| Entity                                                     | Document                        | Pipeline Status |
| ---------------------------------------------------------- | ------------------------------- | --------------- |
| [Activity](chembl/activity.md)                             | Entity schema and fields        | Active          |
| [Assay](chembl/assay.md)                                   | Bioassay definitions            | Active          |
| [Molecule](chembl/molecule.md)                             | Chemical compounds              | Active          |
| [Target](chembl/target.md)                                 | Biological targets              | Active          |
| [Assay Parameters](chembl/assay-parameters.md)             | Assay parameter definitions     | Active          |
| [Cell Line](chembl/cell-line.md)                           | Cell line data                  | Active          |
| [Compound Record](chembl/compound-record.md)               | Compound records                | Active          |
| [Publication](chembl/publication.md)                       | Literature references           | Active          |
| [Publication Similarity](chembl/publication-similarity.md) | Publication similarity          | Active          |
| [Publication Term](chembl/publication-term.md)             | Publication terms               | Active          |
| [Protein Class](chembl/protein-class.md)                   | Protein classification          | Active          |
| [Subcellular Fraction](chembl/subcellular-fraction.md)     | Subcellular fraction vocabulary | Active          |
| [Target Component](chembl/target-component.md)             | Target components               | Active          |
| [Tissue](chembl/tissue.md)                                 | Tissue and anatomical context   | Active          |

## Provider Configuration

Provider-level configurations are in `configs/providers/{provider}.yaml`,
while pipeline/entity configurations are in `configs/entities/{provider}/`:

```
configs/providers/
- chembl.yaml        # Provider-level source/rate-limit/auth settings
- pubchem.yaml       # Provider-level source/rate-limit/auth settings
- ...

configs/entities/
- chembl/           # ChEMBL pipeline configs
- pubchem/          # PubChem configs
- uniprot/          # UniProt configs
- pubmed/           # PubMed configs
- crossref/         # CrossRef configs
- openalex/         # OpenAlex configs
- semanticscholar/  # SemanticScholar configs
```

## Related Documentation

- [RULES.md](../../00-project/RULES.md) Appendix A - Provider rate limits and libraries
- [03-guides/add-new-source.md](../../03-guides/add-new-source.md) - Adding new providers
- [02-architecture/03-infrastructure-layer.md](../../02-architecture/03-infrastructure-layer.md) - Adapter architecture
- [../normalization/non-chembl-normalization-overview.md](../normalization/non-chembl-normalization-overview.md) - Shared non-ChEMBL normalization governance entrypoint
- [../normalization/publication-normalization.md](../normalization/publication-normalization.md) - Raw provider publication types vs derived harmonized taxonomy
- [../normalization/reference-identifiers.md](../normalization/reference-identifiers.md) - Shared identifier-family normalization policy
