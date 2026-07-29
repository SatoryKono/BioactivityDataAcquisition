# openalex_publication passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:openalex_publication`
- Schema: `1.0.0`
- Source revision: `b502aa73ed561cd30b5317e5531677a073694912`

## Evidence

- `effective_entity_config`: `configs/entities/openalex/publication.yaml`
- `dq_contract`: `configs/contracts/openalex/publication.yaml`

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
        "journal",
        "year",
        "citations",
        "open_access",
        "subjects",
        "doc_type",
        "quality",
        "funding"
      ]
    },
    "contract_ref": "openalex.publication",
    "contract_validation": {
      "status": "resolved_by_runtime_contract",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {}
  },
  "identity": {
    "aliases": [],
    "entity": "publication",
    "pipeline_id": "openalex_publication",
    "pipeline_type": "provider_entity",
    "provider": "openalex",
    "status": "active",
    "typed_id": "pipeline:openalex_publication"
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
    "semantic_content_hash": "sha256:5b64b91c35dd3e9e01c0d7ec6177e57860a3fd4d55614da57f1935bc6a1cc3ef",
    "source_revision": "b502aa73ed561cd30b5317e5531677a073694912"
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
        "institutions",
        "journal",
        "year",
        "dates",
        "pagination",
        "citations",
        "open_access",
        "subjects",
        "publisher",
        "funding",
        "doc_type",
        "quality",
        "language",
        "dq"
      ]
    },
    "dq_execution": {
      "hard_fail_threshold": 0.5,
      "invalid_record_policy": "quarantine",
      "soft_fail_threshold": 0.05,
      "strict_validation": false
    },
    "write": {}
  },
  "source_references": [
    {
      "path": "configs/entities/openalex/publication.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/openalex/publication.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
