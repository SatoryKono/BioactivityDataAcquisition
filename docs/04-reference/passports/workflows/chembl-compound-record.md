# chembl_compound_record passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_compound_record`
- Schema: `1.0.0`
- Source revision: `b44143a03ad996f0be3aab44768cadfb05ccde94`

## Evidence

- `workflow_config`: `configs/workflows/chembl_compound_record.yaml`
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
    "mermaid": "flowchart TD\n  run_chembl_compound_record[\"chembl_compound_record\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_compound_record",
        "step_id": "run_chembl_compound_record"
      }
    ],
    "topological_order": [
      "run_chembl_compound_record"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_compound_record",
    "version": "1.0.0",
    "workflow_id": "chembl_compound_record"
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
    "semantic_content_hash": "sha256:7eaf09b9c73e2d7681c3879ff8e46d9d48320f5d8f1dfcbadb109aff83b5af61",
    "source_revision": "b44143a03ad996f0be3aab44768cadfb05ccde94"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_compound_record.yaml",
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
