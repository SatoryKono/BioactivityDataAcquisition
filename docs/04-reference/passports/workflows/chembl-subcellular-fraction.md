# chembl_subcellular_fraction passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_subcellular_fraction`
- Schema: `1.0.0`
- Source revision: `1a62d79f7f55b7972f7e11c78abedd8aedf39bf6`

## Evidence

- `workflow_config`: `configs/workflows/chembl_subcellular_fraction.yaml`
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
    "mermaid": "flowchart TD\n  run_chembl_subcellular_fraction[\"chembl_subcellular_fraction\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_subcellular_fraction",
        "step_id": "run_chembl_subcellular_fraction"
      }
    ],
    "topological_order": [
      "run_chembl_subcellular_fraction"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_subcellular_fraction",
    "version": "1.0.0",
    "workflow_id": "chembl_subcellular_fraction"
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
    "semantic_content_hash": "sha256:0bf1bb4dbe175d830e7ab1b8e7d6e51a5af7178aa195e2d47b51919af1999b26",
    "source_revision": "1a62d79f7f55b7972f7e11c78abedd8aedf39bf6"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_subcellular_fraction.yaml",
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
