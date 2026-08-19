# TYP-RF RF-001 baseline

- origin/main at capture: `1c9e9682b307d34ed573b64bd4adda7fb3e67f9a`
- mypy errors: **36** in **21** files
- ruff RUF022: clean on current origin/main campaign surfaces
- RF-002: retarget import, do not stub `bioetl.domain.chembl.protein_classification`
- Evidence hashes: RF-007 separate PR
- After typing (this PR): mypy 0 / 2440 files

## Assignment

### RF-002 (1)

- `src/bioetl/application/services/protein/_classification_resolution_support.py:10` `import-not-found` — Cannot find implementation or library stub for module named "bioetl.domain.chembl.protein_classification"

### RF-003 (11)

- `src/bioetl/application/services/execution/_pipeline_runner_support.py:181` `redundant-cast` — Redundant cast to "RunResult"
- `src/bioetl/application/services/execution/_pipeline_runner_support.py:189` `redundant-cast` — Redundant cast to "RunResult"
- `src/bioetl/application/services/execution/_pipeline_runner_support.py:251` `no-untyped-def` — Function is missing a type annotation for one or more parameters
- `src/bioetl/application/services/execution/_pipeline_runner_support.py:276` `no-untyped-def` — Function is missing a type annotation
- `src/bioetl/application/services/execution/pipeline_runner_service.py:220` `no-untyped-def` — Function is missing a type annotation for one or more parameters
- `src/bioetl/application/services/execution/pipeline_runner_service.py:232` `no-untyped-call` — Call to untyped function "create_execution_runner_audited" in typed context
- `src/bioetl/application/services/execution/pipeline_runner_service.py:233` `arg-type` — Argument 1 to "create" of "RunnerFactoryPort" has incompatible type "object"; expected "PipelineRunContext"
- `src/bioetl/application/services/execution/pipeline_runner_service.py:241` `arg-type` — Argument "run_logger" to "_execute_pipeline" of "PipelineRunnerService" has incompatible type "object"; expected "LoggerPort"
- `src/bioetl/application/services/execution/pipeline_runner_service.py:243` `arg-type` — Argument "run_id" to "_execute_pipeline" of "PipelineRunnerService" has incompatible type "UUID"; expected "RunID"
- `src/bioetl/application/services/execution/pipeline_runner_service.py:245` `arg-type` — Argument "started_at" to "_execute_pipeline" of "PipelineRunnerService" has incompatible type "object"; expected "datetime"
- `src/bioetl/application/services/execution/pipeline_runner_service.py:246` `arg-type` — Argument "started_monotonic" to "_execute_pipeline" of "PipelineRunnerService" has incompatible type "object"; expected "float"

### RF-004 (9)

- `src/bioetl/infrastructure/control_plane/_file_artifact_lifecycle_refs.py:194` `no-untyped-def` — Function is missing a type annotation for one or more parameters
- `src/bioetl/infrastructure/control_plane/_file_artifact_lifecycle_refs.py:211` `no-untyped-def` — Function is missing a type annotation for one or more parameters
- `src/bioetl/infrastructure/control_plane/_file_artifact_lifecycle_refs.py:225` `no-untyped-def` — Function is missing a type annotation for one or more parameters
- `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation_support.py:342` `attr-defined` — "object" has no attribute "write_reconcile_debug_artifacts"
- `src/bioetl/interfaces/http/_health_server_checkpoint_freshness.py:82` `attr-defined` — "object" has no attribute "resolved_via"
- `src/bioetl/interfaces/http/_health_server_checkpoint_freshness.py:98` `attr-defined` — "object" has no attribute "resolved_via"
- `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation.py:22` `attr-defined` — Module "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support" has no attribute "log_reconciliation_started"; maybe "log_reconciliation"?
- `src/bioetl/composition/factories/pipeline/_runner_assembly_support.py:104` `arg-type` — Argument "metrics" to "ProviderHealthMonitor" has incompatible type "object"; expected "MetricsPort"
- `src/bioetl/composition/factories/pipeline/_runner_assembly_support.py:120` `arg-type` — Argument "health_monitor" to "HealthAggregator" has incompatible type "object"; expected "HealthMonitorPort | None"

### RF-005 (15)

- `src/bioetl/domain/run_reports/workflow_reasons.py:20` `redundant-cast` — Redundant cast to "Sequence[object]"
- `src/bioetl/domain/types/gold_contracts_rules.py:204` `redundant-cast` — Redundant cast to "int | float"
- `src/bioetl/domain/types/gold_contracts_rules.py:205` `redundant-cast` — Redundant cast to "int | float"
- `src/bioetl/application/services/run_reports/writer.py:213` `redundant-cast` — Redundant cast to "PipelineRunReport"
- `src/bioetl/domain/workflow/_delete_orphans_scope.py:113` `redundant-cast` — Redundant cast to "WorkflowConfig"
- `src/bioetl/infrastructure/storage/silver/delta_write_execution.py:345` `redundant-cast` — Redundant cast to "_DeltaWriteRequest"
- `src/bioetl/domain/behavior/composite_validation_layer.py:92` `redundant-cast` — Redundant cast to "CompositeValidationReport"
- `src/bioetl/domain/behavior/dq_rule_evaluator.py:164` `redundant-cast` — Redundant cast to "DQRuleOutcome"
- `src/bioetl/application/services/workflow/workflow_runner_reports.py:148` `redundant-cast` — Redundant cast to "WorkflowRunExecutionResult"
- `src/bioetl/application/services/workflow/workflow_runner_reports.py:164` `redundant-cast` — Redundant cast to "WorkflowRunExecutionResult"
- `src/bioetl/application/core/lifecycle/checkpoint_identity_overrides.py:183` `redundant-cast` — Redundant cast to "CheckpointMetadata"
- `src/bioetl/composition/observability.py:166` `redundant-cast` — Redundant cast to "RunnerInputs"
- `src/bioetl/application/core/base_transformer/base.py:40` `redundant-cast` — Redundant cast to "TransformerDependencyContext"
- `src/bioetl/application/services/control_plane/replay/historical_corpus_service.py:93` `attr-defined` — "HistoricalReplayCorpusService" has no attribute "_skipped_bulk_record"
- `src/bioetl/application/services/workflow/workflow_runner_service.py:133` `redundant-cast` — Redundant cast to "WorkflowRunExecutionResult"

