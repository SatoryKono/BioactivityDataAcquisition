# composite_assay passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `composite:composite_assay`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `composite_config`: `configs/composites/assay.yaml`
- `gold_contract`: `configs/contracts/composite/assay.yaml`

## Generated facts

```json
{
  "composite": {
    "cross_validation": {
      "enabled": false,
      "enricher_pairings": [],
      "error_threshold": 2,
      "fuzzy_threshold": 0.8,
      "numeric_tolerance": 0.1,
      "quarantine_threshold": 2,
      "warning_threshold": 1
    },
    "dependencies": [],
    "enrichers": [
      {
        "filter_condition": "cell_id IS NOT NULL",
        "join_keys": [
          "cell_id"
        ],
        "pipeline": "chembl_cell_line",
        "required": false,
        "silver_table": "silver/chembl/cell_line",
        "timeout_seconds": 300
      },
      {
        "filter_condition": "tissue_id IS NOT NULL",
        "join_keys": [
          "tissue_id"
        ],
        "pipeline": "chembl_tissue",
        "required": false,
        "silver_table": "silver/chembl/tissue",
        "timeout_seconds": 300
      }
    ],
    "execution": {
      "checkpoint_enabled": true,
      "max_concurrency": 2,
      "retry": {
        "backoff_multiplier": 2.0,
        "max_attempts": 3
      }
    },
    "invariants": {
      "aggregation_is_explicit": true,
      "conflict_priorities_are_complete": true,
      "join_keys_must_exist_in_seed_or_prior_key_source_output": true,
      "supported_cardinalities": [
        "one_to_one",
        "many_to_one"
      ]
    },
    "merge": {
      "column_groups": [
        {
          "fields": [
            "entity_id",
            "content_hash",
            "_source",
            "_index",
            "_lookup_method",
            "_original_id"
          ],
          "name": "system",
          "pattern": "^_composite_|^_source_providers|^_enrichment_|^_lineage_|^_dq_",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "assay_id",
            "cell_id",
            "tissue_id",
            "target_id",
            "publication_id",
            "src_id",
            "src_assay_id",
            "aidx"
          ],
          "name": "identifiers",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "assay_type",
            "assay_category",
            "assay_test_type",
            "assay_group",
            "assay_pref_name",
            "relationship_type",
            "relationship_description",
            "confidence_score",
            "confidence_description"
          ],
          "name": "classification",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "assay_organism",
            "assay_taxonomy_id",
            "assay_strain",
            "assay_tissue",
            "assay_cell_type",
            "assay_subcellular_fraction"
          ],
          "name": "biological_context",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "assay_description",
            "confidence_score"
          ],
          "name": "description",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "bao_format",
            "bao_label"
          ],
          "name": "ontology",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "cell_name",
            "cell_description",
            "cell_type",
            "cell_source_tissue",
            "cell_source_organism",
            "cell_source_taxonomy_id",
            "cellosaurus_id",
            "clo_id",
            "cl_lincs_id",
            "cell_efo_id"
          ],
          "name": "cell_line",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "tissue_pref_name",
            "tissue_uberon_id",
            "tissue_bto_id",
            "tissue_caloha_id",
            "tissue_efo_id"
          ],
          "name": "tissue",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "variant_accession",
            "variant_isoform",
            "variant_mutation",
            "variant_organism",
            "variant_sequence",
            "variant_taxonomy_id",
            "variant_sequence_json"
          ],
          "name": "variant",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "assay_classifications",
            "assay_parameters"
          ],
          "name": "complex",
          "provider_order": [
            "chembl"
          ]
        }
      ],
      "conflict_resolution": "seed_priority",
      "exclude_fields": [
        "chembl.cell_line.cell_id",
        "chembl.tissue.tissue_id"
      ],
      "output": {
        "gold": "data/output/gold/composite/assay",
        "silver": "data/output/silver/composite/assay"
      },
      "preserve_all_sources": false,
      "sort_by": {
        "gold": [
          "entity_id",
          "assay_id"
        ],
        "silver": [
          "entity_id",
          "assay_id"
        ]
      },
      "strategy": "left_outer"
    },
    "seed": {
      "output_keys": [
        "assay_id",
        "cell_id",
        "tissue_id",
        "target_id",
        "publication_id",
        "assay_type",
        "assay_description"
      ],
      "pipeline": "chembl_assay",
      "silver_table": "silver/chembl/assay"
    },
    "version": "1.0.0"
  },
  "diagnostics": [],
  "execution": {
    "control_plane": {
      "checkpoints": true,
      "run_manifest": true
    }
  },
  "identity": {
    "aliases": [],
    "entity": "assay",
    "pipeline_id": "composite_assay",
    "pipeline_type": "composite",
    "provider": "composite",
    "status": "active",
    "typed_id": "composite:composite_assay"
  },
  "kind": "pipeline",
  "observability": {
    "correlation_fields": [
      "run_id",
      "manifest_id"
    ],
    "metric_labels": [
      "pipeline",
      "run_type",
      "status"
    ]
  },
  "passport_schema_version": "1.0.0",
  "provenance": {
    "projector_version": "1.0.0",
    "semantic_content_hash": "sha256:dd39c6922fbc64494621c6310164ca665743024c778b1e629a642d90f3396a5d",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
  },
  "source_references": [
    {
      "path": "configs/composites/assay.yaml",
      "role": "composite_config"
    },
    {
      "path": "configs/contracts/composite/assay.yaml",
      "role": "gold_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.

## Owner-approved context

- Owner: `BioETL Team`

### Purpose

Assemble assay records with optional cell-line and tissue context.

### Rationale

The composite exposes optional joins without weakening the final Gold contract.

### Known limitations

- Source assays do not always provide cell-line or tissue identifiers.
