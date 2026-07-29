# pubmed_publication passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:pubmed_publication`
- Schema: `1.0.0`
- Source revision: `ec0f2a1d64cc5d30ee263677982ba2f60cfc1172`

## Evidence

- `effective_entity_config`: `configs/entities/pubmed/publication.yaml`
- `dq_contract`: `configs/contracts/pubmed/publication.yaml`

## Generated facts

```json
{
  "bronze": {
    "capability": "append_only_snapshot",
    "content_hash": {
      "exclude": [],
      "include": []
    }
  },
  "diagnostics": [],
  "execution": {
    "cached_bronze_is_mode": true,
    "control_plane": {
      "checkpoints": true,
      "run_ledger": true,
      "run_manifest": true
    }
  },
  "extraction": {
    "request": {
      "endpoint_template": {
        "status": "runtime_resolved"
      },
      "method": {
        "status": "runtime_resolved"
      }
    },
    "source_type": "runtime_resolved",
    "supported_source_modes": [
      "api",
      "cached_bronze"
    ]
  },
  "gold": {
    "column_projection": {
      "exclude_fields": [
        "_dq_*",
        "_source_batch_id",
        "_index",
        "_lookup_method",
        "_original_id"
      ],
      "include_groups": [
        "system",
        "identifiers",
        "title",
        "abstract",
        "authors",
        "affiliations",
        "journal",
        "year",
        "subjects"
      ]
    },
    "contract_ref": "pubmed.publication",
    "contract_validation": {
      "status": "resolved_by_runtime_contract",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {
      "idempotency_contract": "scd2",
      "mode": "scd2",
      "scd_config": {
        "current_flag_col": "_is_current",
        "valid_from_col": "_valid_from",
        "valid_to_col": "_valid_to",
        "version_col": "_version"
      }
    }
  },
  "identity": {
    "aliases": [],
    "entity": "publication",
    "pipeline_id": "pubmed_publication",
    "pipeline_type": "provider_entity",
    "provider": "pubmed",
    "status": "active",
    "typed_id": "pipeline:pubmed_publication"
  },
  "kind": "pipeline",
  "observability": {
    "correlation_fields": [
      "run_id",
      "manifest_id"
    ],
    "metric_labels": [
      "provider",
      "pipeline",
      "run_type",
      "status"
    ]
  },
  "passport_schema_version": "1.0.0",
  "provenance": {
    "projector_version": "1.0.0",
    "semantic_content_hash": "sha256:790b4f6e533862819e3f7098bb1fd368c0e532f74c3216cc62dbb2ce9861b6ed",
    "source_revision": "ec0f2a1d64cc5d30ee263677982ba2f60cfc1172"
  },
  "silver": {
    "column_projection": {
      "exclude_fields": [],
      "include_groups": [
        "system",
        "identifiers",
        "title",
        "abstract",
        "authors",
        "affiliations",
        "journal",
        "year",
        "dates",
        "pagination",
        "citations",
        "subjects",
        "funding",
        "chemicals",
        "doc_type",
        "language",
        "misc",
        "dq"
      ]
    },
    "dq_execution": {
      "hard_fail_threshold": 0.5,
      "invalid_record_policy": "quarantine",
      "soft_fail_threshold": 0.05,
      "strict_validation": false
    },
    "write": {
      "partition_by": []
    }
  },
  "source_references": [
    {
      "path": "configs/entities/pubmed/publication.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/pubmed/publication.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
