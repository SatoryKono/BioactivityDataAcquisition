# chembl_compound_record passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:chembl_compound_record`
- Schema: `1.0.0`
- Source revision: `b502aa73ed561cd30b5317e5531677a073694912`

## Evidence

- `effective_entity_config`: `configs/entities/chembl/compound_record.yaml`
- `dq_contract`: `configs/contracts/chembl/compound_record.yaml`

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
    "contract_ref": "chembl.compound_record",
    "contract_validation": {
      "status": "resolved_by_runtime_contract",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {}
  },
  "identity": {
    "aliases": [],
    "entity": "compound_record",
    "pipeline_id": "chembl_compound_record",
    "pipeline_type": "provider_entity",
    "provider": "chembl",
    "status": "active",
    "typed_id": "pipeline:chembl_compound_record"
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
    "semantic_content_hash": "sha256:39ea654a8ba32d70a635c8fbcaea58d2cc2dbfdab46f3a74f8021f73d174fedf",
    "source_revision": "b502aa73ed561cd30b5317e5531677a073694912"
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
    "write": {}
  },
  "source_references": [
    {
      "path": "configs/entities/chembl/compound_record.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/chembl/compound_record.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
