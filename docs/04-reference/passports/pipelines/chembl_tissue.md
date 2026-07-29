# chembl_tissue passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:chembl_tissue`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `effective_entity_config`: `configs/entities/chembl/tissue.yaml`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/tissue.yaml`

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
    "effective_config_hash": "sha256:97b967fbb3036a8f935a3f83a7baf3e45d0f07cfc16f2a6501f13532a5e9ac7b",
    "projection_profiles": [
      "batch",
      "http"
    ],
    "resilience": {
      "resolution_owner": "UnifiedHTTPClient and provider config",
      "source_refs": [
        "src/bioetl/infrastructure/adapters/http/client.py",
        "configs/providers/chembl.yaml"
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
        "_index"
      ],
      "include_groups": [
        "system",
        "identifiers",
        "business"
      ]
    },
    "contract_ref": "chembl.tissue",
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
      "entity": "tissue",
      "provider": "chembl"
    },
    "entity": "tissue",
    "pipeline_id": "chembl_tissue",
    "pipeline_type": "provider_entity",
    "provider": "chembl",
    "status": "active",
    "typed_id": "pipeline:chembl_tissue"
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
    "semantic_content_hash": "sha256:12c20e767133e9b044676700ca3fa77ddc2375c5cc3e2af401de19b3faf01e35",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
  },
  "silver": {
    "column_projection": {
      "exclude_fields": [],
      "include_groups": [
        "system",
        "identifiers",
        "business"
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
      "path": "configs/entities/chembl/tissue.yaml",
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
      "path": "configs/contracts/chembl/tissue.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
