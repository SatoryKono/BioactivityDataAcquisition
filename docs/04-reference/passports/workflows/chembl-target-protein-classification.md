# chembl_target_protein_classification passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_target_protein_classification`
- Schema: `1.0.0`
- Source revision: `746ac14dd8150d19f4ee92a99b2b91f249875449`

## Evidence

- `workflow_config`: `configs/workflows/chembl_target_protein_classification.yaml`
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
    "edge_count": 4,
    "edges": [
      {
        "from": "run_chembl_protein_class",
        "to": "run_chembl_target_protein_classification"
      },
      {
        "from": "run_chembl_target",
        "to": "run_chembl_target_component"
      },
      {
        "from": "run_chembl_target",
        "to": "run_chembl_target_protein_classification"
      },
      {
        "from": "run_chembl_target_component",
        "to": "run_chembl_target_protein_classification"
      }
    ],
    "mermaid": "flowchart TD\n  run_chembl_protein_class[\"chembl_protein_class\"]\n  run_chembl_target[\"chembl_target\"]\n  run_chembl_target_component[\"chembl_target_component\"]\n  run_chembl_target_protein_classification[\"chembl_target_protein_classification\"]\n  run_chembl_protein_class --> run_chembl_target_protein_classification\n  run_chembl_target --> run_chembl_target_component\n  run_chembl_target --> run_chembl_target_protein_classification\n  run_chembl_target_component --> run_chembl_target_protein_classification\n",
    "step_count": 4,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_target",
        "step_id": "run_chembl_target"
      },
      {
        "depends_on": [
          "run_chembl_target"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_target_component",
        "step_id": "run_chembl_target_component"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_protein_class",
        "step_id": "run_chembl_protein_class"
      },
      {
        "depends_on": [
          "run_chembl_target",
          "run_chembl_target_component",
          "run_chembl_protein_class"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_target_protein_classification",
        "step_id": "run_chembl_target_protein_classification"
      }
    ],
    "topological_order": [
      "run_chembl_protein_class",
      "run_chembl_target",
      "run_chembl_target_component",
      "run_chembl_target_protein_classification"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_target_protein_classification",
    "version": "1.0.0",
    "workflow_id": "chembl_target_protein_classification"
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
    "semantic_content_hash": "sha256:10f2e7302852ac8372299a8a5cccbea0a59437992ca7a8b0394a6321f996956b",
    "source_revision": "746ac14dd8150d19f4ee92a99b2b91f249875449"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_target_protein_classification.yaml",
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

Build target and protein-classification inputs before projecting their derived relationship.

### Rationale

The explicit DAG prevents publication of a derived classification before its inputs complete.

### Known limitations

- Derived output is bounded by the source snapshot represented in the run evidence.
