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
| Chemistry and activity semantics | `activity.py`, `activity_measurement.py`, `activity_concentration.py`, `activity_relation.py`, `activity_type.py`, `chemical.py`, `compound_ids.py`, `molecular_descriptors.py`, `pchembl_value.py`, `_molecular_weight.py` | Immutable measurement, classification, and compound-normalization primitives used across provider ingestion and composite logic. Activity-related public symbols are exposed through the package root `bioetl.domain.value_objects`. |
| DQ and reporting | `dq_anomaly.py`, `dq_metrics.py`, `dq_result.py`, `dq_report.py`, `dq_report_builder.py`, `dq_report_results*.py`, `silver_result.py`, `bronze_result.py` | Quality scoring, anomaly summary, stage outcomes, and report assembly primitives that stay transport-neutral. |
| Publication grouping and output structure | `column_order.py`, `column_qualifier.py`, `_publication_field_group_config.py`, `_publication_field_groups_data.py`, `publication_field_group_types.py`, `protein_class_hierarchy.py` | Stable structural metadata used for field grouping, output projection, and classification boundaries. |
| Runtime and run context | `run_context.py`, `_run_context_models.py`, `_run_context_create_support.py` | Immutable execution-context shapes used to project deterministic run metadata into domain-safe primitives. |

## Complete Module Catalog

Every active module under `src/bioetl/domain/value_objects/` is listed below.
Private-prefixed modules are implementation helpers or shared data fragments, not
separate aggregate roots.

| Module | Family | Purpose |
| --- | --- | --- |
| `__init__.py` | Package API | Re-exports public value-object symbols for stable imports. |
| `_chemical_identifiers.py` | Chemistry identifiers | Shared parsing/normalization helpers for chemical identifiers. |
| `_molecular_weight.py` | Chemistry semantics | Molecular-weight validation and normalization helper. |
| `_publication_field_group_config.py` | Publication output structure | Field-group configuration model used by publication projections. |
| `_publication_field_groups_data.py` | Publication output structure | Canonical publication field-group data definitions. |
| `_publication_year.py` | Publication semantics | Publication-year validation and normalization helper. |
| `_run_context_create_support.py` | Runtime context | Construction support for deterministic `RunContext` creation. |
| `_run_context_models.py` | Runtime context | Internal immutable models used by `RunContext`. |
| `academic_ids.py` | Publication identifiers | Academic identifier value objects such as DOI/ORCID-style identifiers. |
| `activity.py` | Activity semantics | Activity-domain primitive values and semantic helpers. |
| `activity_concentration.py` | Activity semantics | Concentration-specific activity measurements. |
| `activity_confidence.py` | Activity semantics | Confidence and evidence semantics for activity observations. |
| `activity_measurement.py` | Activity semantics | Measurement value objects for activity rows. |
| `activity_relation.py` | Activity semantics | Relation/operator semantics for measured values. |
| `activity_type.py` | Activity semantics | Typed activity classifications. |
| `base.py` | Shared base | Common value-object base behavior. |
| `bronze_result.py` | DQ/reporting | Bronze-stage result value object. |
| `chemical.py` | Chemistry semantics | Chemical-domain primitives and validation helpers. |
| `column_order.py` | Output structure | Stable output column ordering metadata. |
| `column_qualifier.py` | Output structure | Column qualifier semantics. |
| `compound_ids.py` | Chemistry identifiers | Compound identifier value objects. |
| `dq_anomaly.py` | DQ/reporting | DQ anomaly summary primitives. |
| `dq_metrics.py` | DQ/reporting | DQ metric value objects. |
| `dq_metrics_calculations.py` | DQ/reporting | Calculation helpers for DQ metrics. |
| `dq_report.py` | DQ/reporting | DQ report aggregate value object. |
| `dq_report_builder.py` | DQ/reporting | Builder helpers for report value objects. |
| `dq_report_enums.py` | DQ/reporting | Enumerations used by DQ report values. |
| `dq_report_results.py` | DQ/reporting | Public result value objects for DQ reports. |
| `dq_report_results_core.py` | DQ/reporting | Core result model helpers. |
| `dq_report_results_quality.py` | DQ/reporting | Quality-specific result model helpers. |
| `dq_result.py` | DQ/reporting | Generic DQ result value object. |
| `identifiers.py` | Publication identifiers | General identifier primitives. |
| `inchi.py` | Chemistry identifiers | InChI/InChIKey value objects and validation helpers. |
| `molecular_descriptors.py` | Chemistry semantics | Molecular descriptor value objects. |
| `pchembl_value.py` | Activity semantics | pChEMBL value validation and normalization. |
| `protein_class_hierarchy.py` | Classification | Protein-class hierarchy value object. |
| `publication_field_group_types.py` | Publication output structure | Publication field-group type definitions. |
| `publications.py` | Publication semantics | Publication-specific value objects. |
| `run_context.py` | Runtime context | Domain-safe run execution envelope. |
| `silver_result.py` | DQ/reporting | Silver-stage result value object. |
| `taxonomy_id.py` | Provider identifiers | Taxonomy identifier value object. |

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
| `RunContext` | Requires timezone-aware `started_at`, non-empty `pipeline_name` / `provider` / `entity`, and carries replay-critical identity fields such as `execution_fingerprint`, `required_persistence_profile`, `replay_of_run_id`, `replay_of_manifest_id`, and `input_snapshot_fingerprint`. |
| `StageResult` | Requires non-empty stage name, non-negative `records_processed`, and explicit error/completion evidence for failed stages. |

## Replay-Critical Runtime Value Objects

### `RunContext`

Source of truth: `src/bioetl/domain/value_objects/run_context.py`

`RunContext` is the domain-safe execution envelope shared across Medallion
layers. The current implementation keeps replay-sensitive identity outside of
wall-clock lookup at use sites by carrying the already-resolved `started_at`
timestamp and replay anchors inside the immutable value object.

Current invariants from code:

- `started_at` must be timezone-aware.
- `pipeline_name`, `provider`, and `entity` must be non-empty strings.
- replay- and provenance-related fields are explicit optional slots on the
  value object, including `manifest_id`, `execution_fingerprint`,
  `required_persistence_profile`, `replay_of_run_id`,
  `replay_of_manifest_id`, and `input_snapshot_fingerprint`.
- `RunContext.create(...)` derives `pipeline_name` from the provided
  `provider` and `entity`, so callers do not hand-assemble a second naming
  convention.

### `StageResult`

Source of truth:
`src/bioetl/domain/aggregates/pipeline_run_stage_result.py`

Although `StageResult` currently lives under `domain/aggregates/`, it behaves
as the immutable stage-outcome value object consumed by run aggregates.
Validated invariants are:

- `stage` must not be empty.
- `records_processed` must not be negative.
- `FAILED` status requires both `error` and `completed_at`.
- `SUCCESS` and `FAILED` statuses require `completed_at`.

## Related References

- [Aggregates](aggregates.md)
- [Invariants](invariants.md)
- [ADR-048 Domain Schema Boundary](../../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md)
