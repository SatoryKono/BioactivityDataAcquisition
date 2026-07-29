# uniprot_idmapping passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:uniprot_idmapping`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `effective_entity_config`: `configs/entities/uniprot/idmapping.yaml`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/uniprot/idmapping.yaml`

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
        "business"
      ]
    },
    "contract_ref": "uniprot.idmapping",
    "contract_validation": {
      "status": "resolved_by_adr_018",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {}
  },
  "identity": {
    "aliases": [],
    "entity": "idmapping",
    "pipeline_id": "uniprot_idmapping",
    "pipeline_type": "provider_entity",
    "provider": "uniprot",
    "status": "active",
    "typed_id": "pipeline:uniprot_idmapping"
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
    "semantic_content_hash": "sha256:e84ee14b38ed888c4f979f7f36a04afb5be393ad47bdde2772a2241e215cc454",
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
    "write": {}
  },
  "source_references": [
    {
      "path": "configs/entities/uniprot/idmapping.yaml",
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
      "path": "configs/contracts/uniprot/idmapping.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
