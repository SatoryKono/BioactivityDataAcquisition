# chembl_assay_parameters passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:chembl_assay_parameters`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `effective_entity_config`: `configs/entities/chembl/assay_parameters.yaml`
- `dq_contract`: `configs/contracts/chembl/assay_parameters.yaml`

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
        "_index"
      ],
      "include_groups": [
        "system",
        "business"
      ]
    },
    "contract_ref": "chembl.assay_parameters",
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
    "entity": "assay_parameters",
    "pipeline_id": "chembl_assay_parameters",
    "pipeline_type": "provider_entity",
    "provider": "chembl",
    "status": "active",
    "typed_id": "pipeline:chembl_assay_parameters"
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
    "semantic_content_hash": "sha256:a9e3d0e4ab6a4dc7fc305ab0848092cc951fd541ed3ed1084ba06879363b8362",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
  },
  "silver": {
    "column_projection": {
      "exclude_fields": [],
      "include_groups": [
        "system",
        "business",
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
      "partition_by": [
        "parameter_type"
      ]
    }
  },
  "source_references": [
    {
      "path": "configs/entities/chembl/assay_parameters.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/chembl/assay_parameters.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
