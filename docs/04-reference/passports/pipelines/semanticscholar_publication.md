# semanticscholar_publication passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:semanticscholar_publication`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `effective_entity_config`: `configs/entities/semanticscholar/publication.yaml`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/semanticscholar/publication.yaml`

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
    },
    "effective_config_hash": "sha256:7373e34efddd59c63b1efc82f95cb8fbc0734a21b033b6609002260010d7c95c",
    "projection_profiles": [
      "batch",
      "http"
    ],
    "resilience": {
      "resolution_owner": "UnifiedHTTPClient and provider config",
      "source_refs": [
        "src/bioetl/infrastructure/adapters/http/client.py",
        "configs/providers/semanticscholar.yaml"
      ],
      "status": "runtime_resolved"
    }
  },
  "extraction": {
    "request": {
      "endpoint_template": {
        "resolution_inputs": [
          "provider base_url",
          "entity resource mapping"
        ],
        "resolution_owner": "provider adapter",
        "status": "runtime_resolved"
      },
      "method": {
        "resolution_inputs": [
          "effective provider config",
          "adapter request builder"
        ],
        "resolution_owner": "provider adapter",
        "status": "runtime_resolved"
      }
    },
    "source_modes": {
      "cached_bronze": {
        "availability": "runtime_resolved",
        "identity_kind": "execution_mode"
      },
      "declared": [
        "runtime_resolved"
      ]
    },
    "source_type": "runtime_resolved"
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
        "doc_type",
        "citations",
        "open_access",
        "subjects"
      ]
    },
    "contract_ref": "semanticscholar.publication",
    "contract_validation": {
      "status": "resolved_by_adr_018",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {}
  },
  "identity": {
    "aliases": [],
    "derived_source_identity": {
      "data_source_provider": null,
      "entity": "publication",
      "provider": "semanticscholar"
    },
    "entity": "publication",
    "pipeline_id": "semanticscholar_publication",
    "pipeline_type": "provider_entity",
    "provider": "semanticscholar",
    "status": "active",
    "typed_id": "pipeline:semanticscholar_publication"
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
    "semantic_content_hash": "sha256:f51802163632b5793e64e1038b007d92cd613d7d9f42144889cf4e822cc99dc8",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
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
        "doc_type",
        "open_access",
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
      "path": "configs/entities/semanticscholar/publication.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "docs/02-architecture/decisions/ADR-018-gold-strict-validation.md",
      "role": "gold_validation_contract"
    },
    {
      "path": "src/bioetl/domain/_observability_contract_primitives.py",
      "role": "observability_contract"
    },
    {
      "path": "configs/contracts/semanticscholar/publication.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
