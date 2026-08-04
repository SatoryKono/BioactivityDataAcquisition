# chembl_assay_parameters passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_assay_parameters`
- Schema: `1.0.0`
- Source revision: `b44143a03ad996f0be3aab44768cadfb05ccde94`

## Evidence

- `workflow_config`: `configs/workflows/chembl_assay_parameters.yaml`
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
    "mermaid": "flowchart TD\n  run_chembl_assay_parameters[\"chembl_assay_parameters\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_assay_parameters",
        "step_id": "run_chembl_assay_parameters"
      }
    ],
    "topological_order": [
      "run_chembl_assay_parameters"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_assay_parameters",
    "version": "1.0.0",
    "workflow_id": "chembl_assay_parameters"
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
    "semantic_content_hash": "sha256:0b3142f418b4eebb5c1f722ff652e9023a54425ef25f0e018cd65dcb41edc0b2",
    "source_revision": "b44143a03ad996f0be3aab44768cadfb05ccde94"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_assay_parameters.yaml",
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
