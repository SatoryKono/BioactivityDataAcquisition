# uniprot_support_pack passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:uniprot_support_pack`
- Schema: `1.0.0`
- Source revision: `ec48c9da54018a057886a275553e4e0b886997de`

## Evidence

- `workflow_config`: `configs/workflows/uniprot_support_pack.yaml`
- `workflow_control_plane`: `docs/02-architecture/decisions/ADR-047-workflow-control-plane.md`

## Generated facts

```json
{
  "control_plane": {
    "commit_pending_confirmation": true,
    "exclusive_lock": true,
    "force_steps": true,
    "repair_steps": true,
    "resume_last": true,
    "run_ledger_links": true,
    "workflow_manifest": true
  },
  "dag": {
    "edge_count": 0,
    "edges": [],
    "mermaid": "flowchart TD\n  run_uniprot_idmapping[\"uniprot_idmapping\"]\n  run_uniprot_protein[\"uniprot_protein\"]\n",
    "step_count": 2,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "uniprot_protein",
        "step_id": "run_uniprot_protein"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "uniprot_idmapping",
        "step_id": "run_uniprot_idmapping"
      }
    ],
    "topological_order": [
      "run_uniprot_idmapping",
      "run_uniprot_protein"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:uniprot_support_pack",
    "version": "1.0.0",
    "workflow_id": "uniprot_support_pack"
  },
  "kind": "workflow",
  "observability": {
    "correlation_fields": [
      "run_id",
      "manifest_id",
      "workflow_run_id"
    ],
    "metric_labels": [
      "workflow",
      "pipeline",
      "step_kind",
      "status",
      "run_type"
    ],
    "prohibited_metric_labels": [
      "run_id",
      "manifest_id",
      "workflow_run_id",
      "payload_hash",
      "record_id"
    ]
  },
  "passport_schema_version": "1.0.0",
  "provenance": {
    "projector_version": "1.0.0",
    "semantic_content_hash": "sha256:3047b05777e58b59403e1da784676283d545918b137d1b32a857513a3dcf10df",
    "source_revision": "ec48c9da54018a057886a275553e4e0b886997de"
  },
  "source_references": [
    {
      "path": "configs/workflows/uniprot_support_pack.yaml",
      "role": "workflow_config"
    },
    {
      "path": "docs/02-architecture/decisions/ADR-047-workflow-control-plane.md",
      "role": "workflow_control_plane"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.

## Owner-approved context

- Owner: `BioETL Team`

### Purpose

Resolve UniProt mappings before fetching dependent protein records.

### Rationale

The workflow preserves the mapping result as the typed handoff between executable pipelines.

### Known limitations

- Unmapped identifiers remain explicit and do not trigger a protein fetch.
