# chembl_assay passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_assay`
- Schema: `1.0.0`
- Source revision: `ee78e9542dedc39dc8596da44e8692d40bd31f6b`

## Evidence

- `workflow_config`: `configs/workflows/chembl_assay.yaml`
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
    "mermaid": "flowchart TD\n  run_chembl_assay[\"chembl_assay\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_assay",
        "step_id": "run_chembl_assay"
      }
    ],
    "topological_order": [
      "run_chembl_assay"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_assay",
    "version": "1.0.0",
    "workflow_id": "chembl_assay"
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
    "semantic_content_hash": "sha256:cbbf739f9469c7d16e0637383dd9dc0428b1b88f4851181780bf7df4897f4a21",
    "source_revision": "ee78e9542dedc39dc8596da44e8692d40bd31f6b"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_assay.yaml",
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
