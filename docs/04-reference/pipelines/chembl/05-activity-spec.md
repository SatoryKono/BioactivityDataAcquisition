______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-28'

______________________________________________________________________

# ChEMBL Activity Pipeline Specification

*Version 2.0.0 | Updated: 2026-03-10 | Current-state reference*

______________________________________________________________________

## 1. Identification

| Parameter        | Value                                                                        |
| ---------------- | ---------------------------------------------------------------------------- |
| **Pipeline ID**  | `chembl_activity`                                                            |
| **Provider**     | `chembl`                                                                     |
| **Entity**       | `activity`                                                                   |
| **Endpoint**     | `https://www.ebi.ac.uk/chembl/api/data/activity`                             |
| **HTTP stack**   | Unified httpx-based adapters in `src/bioetl/infrastructure/adapters/chembl/` |
| **Auth type**    | Public API                                                                   |
| **Rate limit**   | `3 req/sec` (`configs/providers/chembl.yaml`)                                |
| **Architecture** | Local-Only runtime (ADR-010)                                                 |

## 2. Current Runtime Behavior

`chembl_activity` is an active Bronze + Silver pipeline. The current config
does **not** emit Gold output.

| Layer      | Status   | Source of truth                         |
| ---------- | -------- | --------------------------------------- |
| **Bronze** | Enabled  | Provider fetch + raw persistence        |
| **Silver** | Enabled  | `configs/entities/chembl/activity.yaml` |
| **Gold**   | Disabled | `pipeline.sink.gold.enabled: false`     |

Key active config:

```yaml
version: 1.0.0
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  business_primary_keys: [activity_id]
  batch_size: 1000
  sink:
    silver:
      mode: merge
    gold:
      enabled: false
```

## 3. Data Model Summary

Primary identifiers and common business fields are defined in
`configs/entities/chembl/activity.yaml` under `schema.column_groups.business`.

Representative fields:

- `activity_id`
- `assay_id`
- `molecule_id`
- `target_id`
- `publication_id`
- `publication_doi`
- `publication_pmid`
- `publication_pmc_id`
- `standard_type`
- `standard_relation`
- `standard_value`
- `standard_units`
- `pchembl_value`
- `data_validity_comment`
- `bao_endpoint_iri`
- `bao_format_iri`
- `bao_ontology_version`
- `uo_unit_iri`
- `uo_ontology_version`
- `qudt_unit_iri`
- `qudt_ontology_version`
- `canonical_smiles`
- `target_pref_name`
- `assay_type`

> **Notice**: This document is a canonical compact summary. For the most current information, always refer to the active entity configuration at `configs/entities/chembl/activity.yaml` and the [ChEMBL provider reference](../../providers/chembl/activity.md).

Publication identifiers are implemented end-to-end in the activity transformer:
canonical `publication_doi`, `publication_pmid`, and `publication_pmc_id`
fields are preferred, while `doi`/`document_doi`,
`pmid`/`pubmed_id`/`document_pubmed_id`, and
`pmc_id`/`document_pmc_id` remain accepted input aliases. BAO/UO/QUDT token
fields remain backward-compatible, with companion IRI/version/mapping-status
fields carrying the machine-readable ontology contract.

The canonical naming policy is `snake_case`. Legacy hyphenated field names are
historical only and should not be used in new configs or examples.

## 4. Validation and Quality

Active validation is driven by the `quality` section of
`configs/entities/chembl/activity.yaml`.

Current examples:

- `activity_id` is required
- `standard_value` must be non-negative and below `1_000_000_000`
- `pchembl_value` must be between `0` and `15`
- `standard_type` and `standard_units` are restricted by configured enums

Silver output keeps business, system, and DQ fields. Gold-only filtering is not
part of the current runtime for this pipeline because Gold is disabled.

## 5. Storage Behavior

### Bronze

```text
Path: data/output/bronze/chembl/activity/
Format: JSONL + compression
Mode: append-only
```

### Silver

```text
Path: data/output/silver/chembl/activity/
Format: Delta Lake
Mode: merge
Primary key semantics: activity_id
```

### Gold

```text
Disabled for the active chembl_activity pipeline
```

If Gold is re-enabled in the future, the reference docs must be updated from
the live entity config and contract sources before describing Gold behavior.

## 6. Source Files

| Component                  | Path                                                              |
| -------------------------- | ----------------------------------------------------------------- |
| Pipeline config            | `configs/entities/chembl/activity.yaml`                           |
| Provider config            | `configs/providers/chembl.yaml`                                   |
| Transformer                | `src/bioetl/application/pipelines/chembl/activity_transformer.py` |
| Domain entity              | `src/bioetl/domain/entities/bioactivity/_entity.py`               |
| ChEMBL adapters            | `src/bioetl/infrastructure/adapters/chembl/`                      |
| Canonical Gold contracts   | `src/bioetl/domain/contracts/gold/`                               |
| Generated contract exports | `docs/04-reference/contracts/gold/`                               |

## 7. CLI Usage

```bash
# List available pipelines
bioetl config list-pipelines

# Incremental run
bioetl run --pipeline chembl_activity

# Limited test run
bioetl run --pipeline chembl_activity --limit 100

# Resume from checkpoint
bioetl run --pipeline chembl_activity --resume

# Run from cached Bronze data
bioetl run --pipeline chembl_activity --use-cached-bronze

# Filter run by IDs from CSV
bioetl run --pipeline chembl_activity \
  --input-csv data/filter-ids.csv \
  --filter-column molecule_id \
  --filter-field molecule_id
```

## 8. Notes

- ChEMBL remains a public provider with configured throttling; do not document it as unbounded.
- Gold reference artifacts may exist in generated docs, but they do not imply that
  `chembl_activity` currently writes Gold output.
- For architectural rationale, see ADR-010, ADR-014, ADR-032, ADR-037, and ADR-039.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [activity.md](../../providers/chembl/activity.md)                                        |
| Gold contract export | [chembl_activity_v1.0.json](../../contracts/gold/chembl_activity_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_activity_v1.0.json](../../contracts/gold/chembl_activity_v1.0.json)              |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
