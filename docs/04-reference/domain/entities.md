______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-06'

______________________________________________________________________

# Domain Entities

## Purpose

This page catalogs provider-facing domain entities and DTO models under
`src/bioetl/domain/entities/`.

Entities are **not** aggregate roots. Lifecycle owners remain `Batch`,
`PipelineRun`, and `QuarantineEntry` ([aggregates.md](aggregates.md)).

## Boundary

- **Domain entities (dataclass):** validated record shapes with lineage fields
  (`run_id`, `content_hash`, …).
- **DTO models (Pydantic):** adapter return types with `extra='forbid'` and
  `frozen=True`; transformers map DTOs into domain entities.
- **Pandera schemas:** live in `src/bioetl/domain/schemas/` per
  [ADR-048](../../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md).

Public lazy exports: `bioetl.domain.entities` (`entities/__init__.py`).

## Module Catalog

| Module | Provider / family | Role |
| --- | --- | --- |
| `base.py` | shared | `BaseEntity` lineage base |
| `bioactivity/` | ChEMBL activity | `Bioactivity`, `BioactivityState`, converters |
| `chembl.py` | ChEMBL | Pydantic DTO records (`ActivityRecord`, `AssayRecord`, …) |
| `chembl_activity.py` | ChEMBL | `Assay` domain entity |
| `chembl_assay_parameters.py` | ChEMBL | `AssayParameters` |
| `chembl_compound_record.py` | ChEMBL | `CompoundRecord` |
| `chembl_structures.py` | ChEMBL | `Target`, `Molecule`, `ChemblPublication`, reference structures |
| `chembl_structures_foundation.py` | ChEMBL | foundation/reference models (`CellLine`, …) |
| `chembl_structures_molecules.py` | ChEMBL | molecule-focused structure models |
| `chembl_subcellular_fraction.py` | ChEMBL | `SubcellularFraction` |
| `chembl_tissue.py` | ChEMBL | `Tissue` |
| `publication_base.py` | publication composite | `PublicationEntityBase` shared projection |
| `crossref.py` | CrossRef | `CrossRefPublicationEntity`, `PublicationRecord` DTO |
| `openalex.py` | OpenAlex | `OpenAlexPublicationEntity` |
| `pubmed.py` | PubMed | `PubMedPublicationEntity`, `ArticleRecord` DTO |
| `semanticscholar.py` | Semantic Scholar | `SemanticScholarPublicationEntity` |
| `pubchem.py` | PubChem | `PubchemMolecule`, `PubchemMoleculeRecord` DTO |
| `uniprot.py` | UniProt | `UniprotTarget` |

Private helper modules (`_chembl_*_models.py`) hold shared dataclass fragments;
they are implementation structure, not separate published entity roots.

## Exported Symbols by Pipeline

| Pipeline | Primary entity / DTO symbols | Source module |
| --- | --- | --- |
| `chembl_activity` | `Bioactivity`, `ActivityRecord` | `bioactivity/`, `chembl.py` |
| `chembl_assay` | `Assay`, `AssayRecord` | `chembl_activity.py`, `chembl.py` |
| `chembl_assay_parameters` | `AssayParameters` | `chembl_assay_parameters.py` |
| `chembl_cell_line` | `CellLine`, `CellLineRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_compound_record` | `CompoundRecord`, `CompoundLinkRecord` | `chembl_compound_record.py`, `chembl.py` |
| `chembl_molecule` | `Molecule`, `MoleculeRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_protein_class` | `ProteinClassification` | `chembl_structures.py` |
| `chembl_publication` | `ChemblPublication`, `ChemblPublicationRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_publication_similarity` | `ChemblPublicationSimilarity`, `PublicationSimilarityRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_publication_term` | `ChemblPublicationTerm`, `ChemblPublicationTermRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_subcellular_fraction` | `SubcellularFraction` | `chembl_subcellular_fraction.py` |
| `chembl_target` | `Target`, `TargetRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_target_component` | `TargetComponent`, `TargetComponentRecord` | `chembl_structures.py`, `chembl.py` |
| `chembl_target_protein_classification` | `TargetProteinClassification` | `chembl_structures.py` |
| `chembl_tissue` | `Tissue`, `TissueRecord` | `chembl_tissue.py`, `chembl.py` |
| `pubchem_compound` | `PubchemMolecule`, `PubchemMoleculeRecord` | `pubchem.py` |
| `uniprot_protein` | `UniprotTarget` | `uniprot.py` |
| `pubmed_publication` | `PubMedPublicationEntity`, `ArticleRecord` | `pubmed.py` |
| `crossref_publication` | `CrossRefPublicationEntity`, `PublicationRecord` | `crossref.py` |
| `openalex_publication` | `OpenAlexPublicationEntity` | `openalex.py` |
| `semanticscholar_publication` | `SemanticScholarPublicationEntity` | `semanticscholar.py` |
| `composite_publication` | `PublicationEntityBase` + provider entities | `publication_base.py` + publication modules |

Composite activity/assay/molecule/target entities are assembled in application
composite merge paths; see [composite pipeline specs](../pipelines/composite/).

## Related References

- [Domain Layer (architecture)](../../02-architecture/01-domain-layer.md) §2.3
- [Provider specs](../providers/)
- [Pipeline catalog](../pipeline-catalog.md)
- [Aggregates](aggregates.md)
