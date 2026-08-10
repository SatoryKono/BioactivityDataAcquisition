# chembl_protein_class passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_protein_class`
- Schema: `1.0.0`
- Source revision: `f68e103f6e3bbced84a59770fbaa51353306fb3a`

## Evidence

- `workflow_config`: `configs/workflows/chembl_protein_class.yaml`
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
    "mermaid": "flowchart TD\n  run_chembl_protein_class[\"chembl_protein_class\"]\n",
    "step_count": 1,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_protein_class",
        "step_id": "run_chembl_protein_class"
      }
    ],
    "topological_order": [
      "run_chembl_protein_class"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_protein_class",
    "version": "1.0.0",
    "workflow_id": "chembl_protein_class"
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
    "semantic_content_hash": "sha256:c2c883371501a1d4f646be76bcc1372a4cf1051c36717ed6adce8cc63d497938",
    "source_revision": "f68e103f6e3bbced84a59770fbaa51353306fb3a"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_protein_class.yaml",
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
