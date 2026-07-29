# chembl_protein_class passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:chembl_protein_class`
- Schema: `1.0.0`
- Source revision: `ec0f2a1d64cc5d30ee263677982ba2f60cfc1172`

## Evidence

- `effective_entity_config`: `configs/entities/chembl/protein_class.yaml`
- `dq_contract`: `configs/contracts/chembl/protein_class.yaml`

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
    "contract_ref": "chembl.protein_class",
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
    "entity": "protein_class",
    "pipeline_id": "chembl_protein_class",
    "pipeline_type": "provider_entity",
    "provider": "chembl",
    "status": "active",
    "typed_id": "pipeline:chembl_protein_class"
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
    "semantic_content_hash": "sha256:be1d7bfcea4a9da99683c32a84a180d747017f3b052b0bbf6e3e1178fa613247",
    "source_revision": "ec0f2a1d64cc5d30ee263677982ba2f60cfc1172"
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
        "class_level"
      ]
    }
  },
  "source_references": [
    {
      "path": "configs/entities/chembl/protein_class.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/chembl/protein_class.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
