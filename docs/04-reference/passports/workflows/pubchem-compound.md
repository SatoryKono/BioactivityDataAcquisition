# pubchem_compound passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:pubchem_compound`
- Schema: `1.0.0`
- Source revision: `dc9df1ebc45136000f02821f185b8a1dfad53638`

## Evidence

- `workflow_config`: `configs/workflows/pubchem_compound.yaml`
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
    "mermaid": "flowchart TD\n  run_pubchem_compound[\"pubchem_compound\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "pubchem_compound",
        "step_id": "run_pubchem_compound"
      }
    ],
    "topological_order": [
      "run_pubchem_compound"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:pubchem_compound",
    "version": "1.0.0",
    "workflow_id": "pubchem_compound"
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
    "semantic_content_hash": "sha256:a589b3d2dccc5c58d72f52421153e318f063a0cd7a7f7a39c9e25c7c7460db9c",
    "source_revision": "dc9df1ebc45136000f02821f185b8a1dfad53638"
  },
  "source_references": [
    {
      "path": "configs/workflows/pubchem_compound.yaml",
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
