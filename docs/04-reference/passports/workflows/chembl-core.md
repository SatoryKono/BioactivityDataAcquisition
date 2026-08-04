# chembl_core passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:chembl_core`
- Schema: `1.0.0`
- Source revision: `1a62d79f7f55b7972f7e11c78abedd8aedf39bf6`

## Evidence

- `workflow_config`: `configs/workflows/chembl_core.yaml`
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
    "edge_count": 5,
    "edges": [
      {
        "from": "chembl_activity_ingest",
        "to": "summarize_core_extracts"
      },
      {
        "from": "chembl_assay_ingest",
        "to": "reconcile_assay_target_orphans"
      },
      {
        "from": "chembl_assay_ingest",
        "to": "summarize_core_extracts"
      },
      {
        "from": "chembl_target_ingest",
        "to": "reconcile_assay_target_orphans"
      },
      {
        "from": "chembl_target_ingest",
        "to": "summarize_core_extracts"
      }
    ],
    "mermaid": "flowchart TD\n  chembl_activity_ingest[\"chembl_activity\"]\n  chembl_assay_ingest[\"chembl_assay\"]\n  chembl_target_ingest[\"chembl_target\"]\n  reconcile_assay_target_orphans[\"reconcile_foreign_keys\"]\n  summarize_core_extracts[\"summarize_upstream_outputs\"]\n  chembl_activity_ingest --> summarize_core_extracts\n  chembl_assay_ingest --> reconcile_assay_target_orphans\n  chembl_assay_ingest --> summarize_core_extracts\n  chembl_target_ingest --> reconcile_assay_target_orphans\n  chembl_target_ingest --> summarize_core_extracts\n",
    "step_count": 5,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_activity",
        "run_options": {
          "limit": 250
        },
        "step_id": "chembl_activity_ingest"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_assay",
        "run_options": {
          "limit": 250
        },
        "step_id": "chembl_assay_ingest"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "chembl_target",
        "run_options": {
          "limit": 250
        },
        "step_id": "chembl_target_ingest"
      },
      {
        "config": {
          "action": "delete_orphans",
          "mutation_layer": "gold",
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
          "chembl_assay_ingest",
          "chembl_target_ingest"
        ],
        "kind": "transform",
        "step_id": "reconcile_assay_target_orphans",
        "transform_name": "reconcile_foreign_keys"
      },
      {
        "depends_on": [
          "chembl_activity_ingest",
          "chembl_assay_ingest",
          "chembl_target_ingest"
        ],
        "kind": "transform",
        "step_id": "summarize_core_extracts",
        "transform_name": "summarize_upstream_outputs"
      }
    ],
    "topological_order": [
      "chembl_activity_ingest",
      "chembl_assay_ingest",
      "chembl_target_ingest",
      "reconcile_assay_target_orphans",
      "summarize_core_extracts"
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
        "control_plane_projection"
      ],
      "config": {},
      "step_id": "summarize_core_extracts",
      "transform_name": "summarize_upstream_outputs"
    }
  ],
  "identity": {
    "status": "active",
    "typed_id": "workflow:chembl_core",
    "version": "1.0.0",
    "workflow_id": "chembl_core"
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
    "semantic_content_hash": "sha256:70660158eba16dccd689e75213e6619edf5777b8b5b03cee61b91e657576cf2c",
    "source_revision": "1a62d79f7f55b7972f7e11c78abedd8aedf39bf6"
  },
  "source_references": [
    {
      "path": "configs/workflows/chembl_core.yaml",
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

Coordinate the core ChEMBL ingest and reconcile current Gold assay references.

### Rationale

ADR-055 retains reconciliation inside the ADR-047 governed workflow surface.

### Known limitations

- Foreign-key reconciliation is an explicit data-plane workflow step, not orchestration-only behavior.
