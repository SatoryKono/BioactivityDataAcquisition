# chembl_publication passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `pipeline:chembl_publication`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `effective_entity_config`: `configs/entities/chembl/publication.yaml`
- `gold_validation_contract`: `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
- `observability_contract`: `src/bioetl/domain/_observability_contract_primitives.py`
- `dq_contract`: `configs/contracts/chembl/publication.yaml`

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
    "effective_config_hash": "sha256:fed7539227fc90827d33fb755659a378db56b54d8ed53d374f3f113c5f3e68bf",
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
        "_index",
        "_lookup_method",
        "_original_id",
        "pmc_id",
        "publication_type_unified",
        "publication_subclass",
        "publication_class",
        "oa_status",
        "affiliation_list",
        "author_orcids",
        "is_oa",
        "issn_list",
        "language",
        "publication_date"
      ],
      "include_groups": [
        "system",
        "identifiers",
        "title",
        "abstract",
        "authors",
        "journal",
        "year",
        "pagination",
        "doc_type"
      ]
    },
    "contract_ref": "chembl.publication",
    "contract_validation": {
      "status": "resolved_by_adr_018",
      "strict": true
    },
    "contract_version": "1.0.0",
    "write": {
      "enabled": true,
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
    "derived_source_identity": {
      "data_source_provider": null,
      "entity": "publication",
      "provider": "chembl"
    },
    "entity": "publication",
    "pipeline_id": "chembl_publication",
    "pipeline_type": "provider_entity",
    "provider": "chembl",
    "status": "active",
    "typed_id": "pipeline:chembl_publication"
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
    "semantic_content_hash": "sha256:23dedf7528a08265a8323a17d69f4256d53c31f000dc247cb332495da8472163",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
  },
  "silver": {
    "column_projection": {
      "exclude_fields": [
        "affiliation_list",
        "author_orcids",
        "is_oa",
        "issn_list",
        "language",
        "publication_date"
      ],
      "include_groups": [
        "system",
        "identifiers",
        "title",
        "abstract",
        "authors",
        "journal",
        "year",
        "pagination",
        "doc_type",
        "open_access",
        "provider_ids",
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
      "path": "configs/entities/chembl/publication.yaml",
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
      "path": "configs/contracts/chembl/publication.yaml",
      "role": "dq_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
