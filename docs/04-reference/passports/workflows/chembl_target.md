# chembl_target passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_target`
- Schema: `1.0.0`
- Source revision: `b502aa73ed561cd30b5317e5531677a073694912`

## Evidence

- `workflow_config`: `configs/workflows/chembl_target.yaml`
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
        "pipeline_name": "chembl_target",
        "step_id": "run_chembl_target"
      }
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_target",
    "version": "1.0.0",
    "workflow_id": "chembl_target"
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
    "semantic_content_hash": "sha256:e385ed0dc0bb661463b66b521d16b852d279826068055db71ea1354f2737da0b",
    "source_revision": "b502aa73ed561cd30b5317e5531677a073694912"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_target.yaml",
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
