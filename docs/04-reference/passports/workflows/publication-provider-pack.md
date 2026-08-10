# publication_provider_pack passport

> Generated documentation projection. Do not edit manually.

- Kind: `workflow`
- Typed identity: `workflow:publication_provider_pack`
- Schema: `1.0.0`
- Source revision: `d45de38667a42e416864815ea3a35e962763761e`

## Evidence

- `workflow_config`: `configs/workflows/publication_provider_pack.yaml`
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
    "mermaid": "flowchart TD\n  run_crossref_publication[\"crossref_publication\"]\n  run_openalex_publication[\"openalex_publication\"]\n  run_pubmed_publication[\"pubmed_publication\"]\n  run_semanticscholar_publication[\"semanticscholar_publication\"]\n",
    "step_count": 4,
    "steps": [
      {
        "kind": "pipeline",
        "pipeline_name": "crossref_publication",
        "step_id": "run_crossref_publication"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "openalex_publication",
        "step_id": "run_openalex_publication"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "pubmed_publication",
        "step_id": "run_pubmed_publication"
      },
      {
        "kind": "pipeline",
        "pipeline_name": "semanticscholar_publication",
        "step_id": "run_semanticscholar_publication"
      }
    ],
    "topological_order": [
      "run_crossref_publication",
      "run_openalex_publication",
      "run_pubmed_publication",
      "run_semanticscholar_publication"
    ]
  },
  "diagnostics": [],
  "external_data_operations": [],
  "identity": {
    "status": "active",
    "typed_id": "workflow:publication_provider_pack",
    "version": "1.0.0",
    "workflow_id": "publication_provider_pack"
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
    "semantic_content_hash": "sha256:b7e1e544b55a11eeecef4fc54abf4e06b2ad905ff604973ee2218f89ff749089",
    "source_revision": "d45de38667a42e416864815ea3a35e962763761e"
  },
  "source_references": [
    {
      "path": "configs/workflows/publication_provider_pack.yaml",
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

Run publication providers as an explicit multi-provider workflow.

### Rationale

Separate pipeline identities are retained while workflow-level ordering and recovery stay visible.

### Known limitations

- Provider coverage and freshness can differ without implying cross-provider equivalence.
