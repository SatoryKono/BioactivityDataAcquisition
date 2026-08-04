# chembl_baseline passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_baseline`
- Schema: `1.0.0`
- Source revision: `dc9df1ebc45136000f02821f185b8a1dfad53638`

## Evidence

- `workflow_config`: `configs/workflows/chembl_baseline.yaml`
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
    "edge_count": 8,
    "edges": [
      {
        "from": "reconcile_assay_publication_orphans",
        "to": "reconcile_target_assay_orphans"
      },
      {
        "from": "reconcile_assay_target_orphans",
        "to": "reconcile_assay_publication_orphans"
      },
      {
        "from": "reconcile_target_assay_orphans",
        "to": "reconcile_publication_assay_orphans"
      },
      {
        "from": "run_chembl_assay",
        "to": "reconcile_assay_target_orphans"
      },
      {
        "from": "run_chembl_assay",
        "to": "run_chembl_target"
      },
      {
        "from": "run_chembl_publication",
        "to": "reconcile_assay_publication_orphans"
      },
      {
        "from": "run_chembl_target",
        "to": "reconcile_assay_target_orphans"
      },
      {
        "from": "run_chembl_target",
        "to": "run_chembl_publication"
      }
    ],
    "mermaid": "flowchart TD\n  reconcile_assay_publication_orphans[\"reconcile_foreign_keys\"]\n  reconcile_assay_target_orphans[\"reconcile_foreign_keys\"]\n  reconcile_publication_assay_orphans[\"reconcile_foreign_keys\"]\n  reconcile_target_assay_orphans[\"reconcile_foreign_keys\"]\n  run_chembl_assay[\"chembl_assay\"]\n  run_chembl_publication[\"chembl_publication\"]\n  run_chembl_target[\"chembl_target\"]\n  reconcile_assay_publication_orphans --> reconcile_target_assay_orphans\n  reconcile_assay_target_orphans --> reconcile_assay_publication_orphans\n  reconcile_target_assay_orphans --> reconcile_publication_assay_orphans\n  run_chembl_assay --> reconcile_assay_target_orphans\n  run_chembl_assay --> run_chembl_target\n  run_chembl_publication --> reconcile_assay_publication_orphans\n  run_chembl_target --> reconcile_assay_target_orphans\n  run_chembl_target --> run_chembl_publication\n",
    "step_count": 7,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_assay",
        "step_id": "run_chembl_assay"
      },
      {
        "depends_on": [
          "run_chembl_assay"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_target",
        "step_id": "run_chembl_target"
      },
      {
        "depends_on": [
          "run_chembl_target"
        ],
        "kind": "pipeline",
        "pipeline_name": "chembl_publication",
        "step_id": "run_chembl_publication"
      },
      {
        "config": {
          "action": "delete_orphans",
          "mutation_layer": "gold",
          "nulls_equal": false,
          "primary_keys": [
            "assay_id"
          ],
          "reference_key": "target_id",
          "reference_layer": "gold",
          "reference_table": "chembl.target",
          "source_key": "target_id",
          "source_layer": "gold",
          "source_table": "chembl.assay"
        },
        "depends_on": [
          "run_chembl_assay",
          "run_chembl_target"
        ],
        "kind": "transform",
        "step_id": "reconcile_assay_target_orphans",
        "transform_name": "reconcile_foreign_keys"
      },
      {
        "config": {
          "action": "delete_orphans",
          "mutation_layer": "gold",
          "nulls_equal": false,
          "primary_keys": [
            "assay_id"
          ],
          "reference_key": "publication_id",
          "reference_layer": "gold",
          "reference_table": "chembl.publication",
          "source_key": "publication_id",
          "source_layer": "gold",
          "source_table": "chembl.assay"
        },
        "depends_on": [
          "reconcile_assay_target_orphans",
          "run_chembl_publication"
        ],
        "kind": "transform",
        "step_id": "reconcile_assay_publication_orphans",
        "transform_name": "reconcile_foreign_keys"
      },
      {
        "config": {
          "action": "delete_orphans",
          "mutation_layer": "gold",
          "nulls_equal": false,
          "primary_keys": [
            "target_id"
          ],
          "reference_key": "target_id",
          "reference_layer": "gold",
          "reference_table": "chembl.assay",
          "source_key": "target_id",
          "source_layer": "gold",
          "source_table": "chembl.target"
        },
        "depends_on": [
          "reconcile_assay_publication_orphans"
        ],
        "kind": "transform",
        "step_id": "reconcile_target_assay_orphans",
        "transform_name": "reconcile_foreign_keys"
      },
      {
        "config": {
          "action": "delete_orphans",
          "mutation_layer": "gold",
          "nulls_equal": false,
          "primary_keys": [
            "publication_id"
          ],
          "reference_key": "publication_id",
          "reference_layer": "gold",
          "reference_table": "chembl.assay",
          "source_key": "publication_id",
          "source_layer": "gold",
          "source_table": "chembl.publication"
        },
        "depends_on": [
          "reconcile_target_assay_orphans"
        ],
        "kind": "transform",
        "step_id": "reconcile_publication_assay_orphans",
        "transform_name": "reconcile_foreign_keys"
      }
    ],
    "topological_order": [
      "run_chembl_assay",
      "run_chembl_target",
      "reconcile_assay_target_orphans",
      "run_chembl_publication",
      "reconcile_assay_publication_orphans",
      "reconcile_target_assay_orphans",
      "reconcile_publication_assay_orphans"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [
    {
      "classification": [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation"
      ],
      "config": {
        "action": "delete_orphans",
        "mutation_layer": "gold",
        "nulls_equal": false,
        "primary_keys": [
          "assay_id"
        ],
        "reference_key": "target_id",
        "reference_layer": "gold",
        "reference_table": "chembl.target",
        "source_key": "target_id",
        "source_layer": "gold",
        "source_table": "chembl.assay"
      },
      "step_id": "reconcile_assay_target_orphans",
      "transform_name": "reconcile_foreign_keys"
    },
    {
      "classification": [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation"
      ],
      "config": {
        "action": "delete_orphans",
        "mutation_layer": "gold",
        "nulls_equal": false,
        "primary_keys": [
          "assay_id"
        ],
        "reference_key": "publication_id",
        "reference_layer": "gold",
        "reference_table": "chembl.publication",
        "source_key": "publication_id",
        "source_layer": "gold",
        "source_table": "chembl.assay"
      },
      "step_id": "reconcile_assay_publication_orphans",
      "transform_name": "reconcile_foreign_keys"
    },
    {
      "classification": [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation"
      ],
      "config": {
        "action": "delete_orphans",
        "mutation_layer": "gold",
        "nulls_equal": false,
        "primary_keys": [
          "target_id"
        ],
        "reference_key": "target_id",
        "reference_layer": "gold",
        "reference_table": "chembl.assay",
        "source_key": "target_id",
        "source_layer": "gold",
        "source_table": "chembl.target"
      },
      "step_id": "reconcile_target_assay_orphans",
      "transform_name": "reconcile_foreign_keys"
    },
    {
      "classification": [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation"
      ],
      "config": {
        "action": "delete_orphans",
        "mutation_layer": "gold",
        "nulls_equal": false,
        "primary_keys": [
          "publication_id"
        ],
        "reference_key": "publication_id",
        "reference_layer": "gold",
        "reference_table": "chembl.assay",
        "source_key": "publication_id",
        "source_layer": "gold",
        "source_table": "chembl.publication"
      },
      "step_id": "reconcile_publication_assay_orphans",
      "transform_name": "reconcile_foreign_keys"
    }
  ],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_baseline",
    "version": "1.2.0",
    "workflow_id": "chembl_baseline"
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
    "semantic_content_hash": "sha256:0c4b8bf263380d40361ca35749e64226a7862c11313569d72a65ef08728b0ab6",
    "source_revision": "dc9df1ebc45136000f02821f185b8a1dfad53638"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_baseline.yaml",
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

Build the baseline ChEMBL assay, target, and publication datasets with bidirectional referential reconciliation.

### Rationale

ADR-055 requires the mutation and its recovery boundary to remain explicit in this passport.

### Known limitations

- Four ordered Gold reconciliation steps make transform order semantically relevant.
