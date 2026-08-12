# chembl_reference_pack passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_reference_pack`
- Schema: `1.0.0`
- Source revision: `76f32bb632b55c9960491d8df05abd5a51cf8504`

## Evidence

- `workflow_config`: `configs/workflows/chembl_reference_pack.yaml`
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
    "edge_count": 6,
    "edges": [
      {
        "from": "run_chembl_protein_class",
        "to": "run_chembl_target_protein_classification"
      },
      {
        "from": "run_chembl_publication",
        "to": "run_chembl_publication_similarity"
      },
      {
        "from": "run_chembl_publication",
        "to": "run_chembl_publication_term"
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
    "mermaid": "flowchart TD\n  run_chembl_cell_line[\"chembl_cell_line\"]\n  run_chembl_protein_class[\"chembl_protein_class\"]\n  run_chembl_publication[\"chembl_publication\"]\n  run_chembl_publication_similarity[\"chembl_publication_similarity\"]\n  run_chembl_publication_term[\"chembl_publication_term\"]\n  run_chembl_subcellular_fraction[\"chembl_subcellular_fraction\"]\n  run_chembl_target[\"chembl_target\"]\n  run_chembl_target_component[\"chembl_target_component\"]\n  run_chembl_target_protein_classification[\"chembl_target_protein_classification\"]\n  run_chembl_tissue[\"chembl_tissue\"]\n  run_chembl_protein_class --> run_chembl_target_protein_classification\n  run_chembl_publication --> run_chembl_publication_similarity\n  run_chembl_publication --> run_chembl_publication_term\n  run_chembl_target --> run_chembl_target_component\n  run_chembl_target --> run_chembl_target_protein_classification\n  run_chembl_target_component --> run_chembl_target_protein_classification\n",
    "step_count": 10,
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
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_tissue",
        "step_id": "run_chembl_tissue"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_subcellular_fraction",
        "step_id": "run_chembl_subcellular_fraction"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_cell_line",
        "step_id": "run_chembl_cell_line"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_publication",
        "step_id": "run_chembl_publication"
      },
      {
        "depends_on": [
          "run_chembl_publication"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_publication_term",
        "step_id": "run_chembl_publication_term"
      },
      {
        "depends_on": [
          "run_chembl_publication"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_publication_similarity",
        "step_id": "run_chembl_publication_similarity"
      }
    ],
    "topological_order": [
      "run_chembl_cell_line",
      "run_chembl_protein_class",
      "run_chembl_publication",
      "run_chembl_subcellular_fraction",
      "run_chembl_target",
      "run_chembl_tissue",
      "run_chembl_publication_similarity",
      "run_chembl_publication_term",
      "run_chembl_target_component",
      "run_chembl_target_protein_classification"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_reference_pack",
    "version": "1.0.0",
    "workflow_id": "chembl_reference_pack"
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
    "semantic_content_hash": "sha256:af8a9911fdccdd9c9f1d44175a8b3680d54339214ee098e41d4915489a5bed18",
    "source_revision": "76f32bb632b55c9960491d8df05abd5a51cf8504"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_reference_pack.yaml",
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

Execute the ordered ChEMBL reference-data workflow as one recoverable control-plane unit.

### Rationale

The workflow passport makes cross-pipeline handoffs and recovery boundaries visible.

### Known limitations

- Individual provider results remain independently inspectable and may complete at different times.
