# uniprot_idmapping passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:uniprot_idmapping`
- Schema: `1.0.0`
- Source revision: `3e8cf5528c7b75174ee7fd8de2c51958a0fd6d0c`

## Evidence

- `workflow_config`: `configs/workflows/uniprot_idmapping.yaml`
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
    "mermaid": "flowchart TD\n  run_uniprot_idmapping[\"uniprot_idmapping\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "uniprot_idmapping",
        "step_id": "run_uniprot_idmapping"
      }
    ],
    "topological_order": [
      "run_uniprot_idmapping"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:uniprot_idmapping",
    "version": "1.0.0",
    "workflow_id": "uniprot_idmapping"
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
    "semantic_content_hash": "sha256:936e63203227f577e285dc725be4128ab9d582a950dd2ace418f7faf31ef2721",
    "source_revision": "3e8cf5528c7b75174ee7fd8de2c51958a0fd6d0c"
  },
  "source_references": [
    {
      "path": "configs/workflows/uniprot_idmapping.yaml",
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
