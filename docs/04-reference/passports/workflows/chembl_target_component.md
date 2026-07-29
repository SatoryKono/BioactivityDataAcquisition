# chembl_target_component passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_target_component`
- Schema: `1.0.0`
- Source revision: `ec0f2a1d64cc5d30ee263677982ba2f60cfc1172`

## Evidence

- `workflow_config`: `configs/workflows/chembl_target_component.yaml`
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
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_target_component",
        "step_id": "run_chembl_target_component"
      }
    ],
    "topological_order": [
      "run_chembl_target_component"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_target_component",
    "version": "1.0.0",
    "workflow_id": "chembl_target_component"
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
    "semantic_content_hash": "sha256:a345e1ab54e7d6870fe44ec7cfcc3a32c12f769fd3a7ec5d7aabd9db13425715",
    "source_revision": "ec0f2a1d64cc5d30ee263677982ba2f60cfc1172"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_target_component.yaml",
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
