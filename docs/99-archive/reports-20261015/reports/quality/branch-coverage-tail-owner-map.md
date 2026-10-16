# Branch coverage tail owner map

Issue #8339

- Branch rate (gap report): **86.152%** (threshold 85%)
- Files below 85% branch coverage: **552**

## Priority families

- **infrastructure_quarantine** (min ~24.36%) owner @bioetl-infrastructure
  - tail: src/bioetl/infrastructure/quarantine/status_events.py
- **infrastructure_storage** (min ~26.32%) owner @bioetl-infrastructure
  - tail: src/bioetl/infrastructure/storage/bronze/metadata_snapshot_refs.py
- **application_services** (min ~27.78%) owner @bioetl-application
  - tail: src/bioetl/application/services/control_plane/manifest/inspection_artifact_refs.py
- **infrastructure_observability** (min ~35.29%) owner @bioetl-infrastructure
  - tail: src/bioetl/infrastructure/observability/health_metrics_exposition.py
- **domain_run_reports** (min ~51.28%) owner @bioetl-domain
  - tail: src/bioetl/domain/run_reports/workflow_reasons.py
- **infrastructure_adapters** (min ~57.95%) owner @bioetl-infrastructure
  - tail: src/bioetl/infrastructure/adapters/pubmed/adapter.py
- **interfaces_http** (min ~58.21%) owner @bioetl-interfaces
  - tail: src/bioetl/interfaces/http/_health_server_observability_routing.py
- **application_core** (min ~61.26%) owner @bioetl-application
  - tail: src/bioetl/application/core/batch_writer_columns_mixin.py
- **infrastructure_export** (min ~64.13%) owner @bioetl-infrastructure
  - tail: src/bioetl/infrastructure/export/debug_export_ops.py
- **application_workflow** (min ~64.86%) owner @bioetl-application
  - tail: src/bioetl/application/workflow/transforms/reconcile_rows.py
- **interfaces_cli** (min ~67.5%) owner @bioetl-interfaces
  - tail: src/bioetl/interfaces/cli/commands/domains/health/server_integration_deps.py
- **application_composite** (min ~71.0%) owner @bioetl-application
  - tail: src/bioetl/application/composite/checkpoint/_checkpoint_runtime.py

