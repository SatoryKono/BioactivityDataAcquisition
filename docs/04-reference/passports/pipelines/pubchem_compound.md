# pubchem_compound passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:pubchem_compound`
- Schema: `1.0.0`
- Source revision: `ec0f2a1d64cc5d30ee263677982ba2f60cfc1172`

## Evidence

- `effective_entity_config`: `configs/entities/pubchem/compound.yaml`
- `dq_contract`: `configs/contracts/pubchem/compound.yaml`

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
    "contract_ref": "pubchem.compound",
    "contract_validation": {
      "status": "resolved_by_runtime_contract",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {}
  },
  "identity": {
    "aliases": [],
    "entity": "compound",
    "pipeline_id": "pubchem_compound",
    "pipeline_type": "provider_entity",
    "provider": "pubchem",
    "status": "active",
    "typed_id": "pipeline:pubchem_compound"
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
    "semantic_content_hash": "sha256:0db04561947095b76b42ad9f5b274a04be7a1177146df9717c7adc94c7aa002f",
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
    "write": {}
  },
  "source_references": [
    {
      "path": "configs/entities/pubchem/compound.yaml",
      "role": "effective_entity_config"
    },
    {
      "path": "configs/contracts/pubchem/compound.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
