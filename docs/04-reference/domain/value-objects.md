______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Domain Value Objects

## Purpose

`src/bioetl/domain/value_objects/` contains immutable domain primitives and
typed semantic helpers that keep validation close to the domain boundary.

## Family Catalog

| Family | Representative modules | Semantic role |
| --- | --- | --- |
| Publication and academic identifiers | `academic_ids.py`, `identifiers.py`, `publications.py`, `taxonomy_id.py`, `inchi.py` | Strongly typed identifiers such as DOI, PubMed ID, OpenAlex ID, Semantic Scholar ID, ISSN, ORCID, UniProt ID, and related publication keys. |
| Chemistry and activity semantics | `activity.py`, `activity_measurement.py`, `activity_concentration.py`, `activity_relation.py`, `activity_type.py`, `activity_values.py`, `chemical.py`, `compound_ids.py`, `molecular_descriptors.py`, `pchembl_value.py`, `_molecular_weight.py` | Immutable measurement, classification, and compound-normalization primitives used across provider ingestion and composite logic. |
| DQ and reporting | `dq_anomaly.py`, `dq_metrics.py`, `dq_result.py`, `dq_report.py`, `dq_report_builder.py`, `dq_report_results*.py`, `silver_result.py`, `bronze_result.py` | Quality scoring, anomaly summary, stage outcomes, and report assembly primitives that stay transport-neutral. |
| Publication grouping and output structure | `column_order.py`, `column_qualifier.py`, `_publication_field_group_config.py`, `_publication_field_groups_data.py`, `publication_field_group_types.py`, `protein_class_hierarchy.py` | Stable structural metadata used for field grouping, output projection, and classification boundaries. |
| Runtime and run context | `run_context.py`, `_run_context_models.py`, `_run_context_create_support.py` | Immutable execution-context shapes used to project deterministic run metadata into domain-safe primitives. |

## Design Rules

- Value objects stay immutable and validation-centric.
- They may normalize raw input into canonical forms, but they must not perform
  I/O or depend on infrastructure frameworks.
- They provide typed semantics so aggregate invariants and adapter contracts do
  not fall back to unstructured `str`/`dict` payloads.

## High-Signal Examples

| Value object | Example constraint |
| --- | --- |
| `DOI` | Normalizes URL/prefix forms and requires `10.<digits>/<suffix>` shape. |
| `PubMedId` | Digits only, positive, bounded numeric domain. |
| `OpenAlexId` | Accepts URL form but normalizes to `W<digits>`. |
| `SemanticScholarId` | Requires a 40-character hexadecimal identifier. |
| `UniProtId` | Restricts to supported accession patterns and lengths. |
| `StageResult` | Requires coherent timestamps and failure metadata for failed stages. |

## Related References

- [Aggregates](aggregates.md)
- [Invariants](invariants.md)
- [ADR-048 Domain Schema Boundary](../../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md)
