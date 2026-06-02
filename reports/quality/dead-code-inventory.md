# Dead Code Inventory

- snapshot_date: 2026-06-02
- linked_issue: #4541
- last_reviewed: 2026-06-02
- next_review_by: 2026-08-31
- review_cycle_days: 90
- triaged_entry_count: 18
- repo_wide_zero_import_candidate_count: 41
- repo_wide_classified_zero_import_candidate_count: 41
- repo_wide_untriaged_zero_import_candidate_count: 0
- note: zero static importer count is a review signal, not automatic removal proof
- guardrail: Zero static importer count is a review signal only; removals must still verify public entrypoints and dynamic/plugin import paths.

## Triage Verification

| Entry | Disposition | src importers | Verification |
| --- | --- | ---: | --- |
| `cached_bronze_support_active` | `retain_active` | 1 | `satisfied` |
| `error_handling_support_active` | `retain_active` | 1 | `satisfied` |
| `health_check_observability_active` | `retain_active` | 1 | `satisfied` |
| `health_check_policy_active` | `retain_active` | 1 | `satisfied` |
| `preflight_rules_removed` | `removed` | 0 | `not_applicable` |
| `checkpoint_service_support_removed` | `removed` | 0 | `not_applicable` |
| `checkpoint_state_codec_removed` | `removed` | 0 | `not_applicable` |
| `fsm_helper_active` | `retain_active` | 10 | `satisfied` |
| `runner_merge_stage_flow_removed` | `removed` | 0 | `not_applicable` |
| `column_priority_orderer_active` | `retain_active` | 2 | `satisfied` |
| `merger_input_mixin_active` | `retain_active` | 2 | `satisfied` |
| `runner_support_flow_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_mixin_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_policy_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_runtime_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_types_active` | `retain_active` | 4 | `satisfied` |
| `runtime_models_active` | `retain_active` | 39 | `satisfied` |
| `runtime_wiring_api_active` | `retain_active` | 18 | `satisfied` |

## Repo-wide Zero-import Candidates

| Module | Disposition | Path |
| --- | --- | --- |
| `bioetl.__main__` | `retain_module_entrypoint` | `src/bioetl/__main__.py` |
| `bioetl.application.core.batch_execution_lifecycle` | `retain_public_facade` | `src/bioetl/application/core/batch_execution_lifecycle.py` |
| `bioetl.application.core.batch_execution_run_service` | `retain_public_facade` | `src/bioetl/application/core/batch_execution_run_service.py` |
| `bioetl.application.core.batch_execution_state_service` | `retain_public_facade` | `src/bioetl/application/core/batch_execution_state_service.py` |
| `bioetl.application.core.pipeline_service_protocols` | `retain_public_facade` | `src/bioetl/application/core/pipeline_service_protocols.py` |
| `bioetl.application.pipelines.common.blocks` | `retain_dynamic_entrypoint` | `src/bioetl/application/pipelines/common/blocks.py` |
| `bioetl.application.pipelines.common.publication_strategies` | `retain_canonical_owner_module` | `src/bioetl/application/pipelines/common/publication_strategies.py` |
| `bioetl.application.pipelines.pubmed.strategies` | `retain_canonical_owner_module` | `src/bioetl/application/pipelines/pubmed/strategies.py` |
| `bioetl.application.services._checkpoint_compatibility_runtime_core` | `retain_canonical_owner_module` | `src/bioetl/application/services/_checkpoint_compatibility_runtime_core.py` |
| `bioetl.application.services.control_plane._run_manifest_diagnostics_identity` | `retain_canonical_owner_module` | `src/bioetl/application/services/control_plane/_run_manifest_diagnostics_identity.py` |
| `bioetl.composition.registry` | `retain_public_facade` | `src/bioetl/composition/registry.py` |
| `bioetl.domain.behavior._dq_serializer_html._renderers` | `retain_canonical_owner_module` | `src/bioetl/domain/behavior/_dq_serializer_html/_renderers.py` |
| `bioetl.domain.entities.bioactivity._entity` | `retain_canonical_owner_module` | `src/bioetl/domain/entities/bioactivity/_entity.py` |
| `bioetl.domain.normalization._pubchem_standardization_catalog` | `retain_canonical_owner_module` | `src/bioetl/domain/normalization/_pubchem_standardization_catalog.py` |
| `bioetl.domain.ports.data_normalization` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/data_normalization.py` |
| `bioetl.domain.ports.data_source` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/data_source.py` |
| `bioetl.domain.ports.delta_reader` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/delta_reader.py` |
| `bioetl.domain.ports.export` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/export.py` |
| `bioetl.domain.ports.filtering` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/filtering.py` |
| `bioetl.domain.ports.idmapping` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/idmapping.py` |
| `bioetl.domain.ports.logger_port` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/logger_port.py` |
| `bioetl.domain.ports.pii` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/pii.py` |
| `bioetl.domain.ports.protein_classification` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/protein_classification.py` |
| `bioetl.domain.ports.publication_strategy` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/publication_strategy.py` |
| `bioetl.domain.ports.resilience` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/resilience.py` |
| `bioetl.domain.ports.serialization` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/serialization.py` |
| `bioetl.domain.transformations.drift` | `retain_canonical_owner_module` | `src/bioetl/domain/transformations/drift.py` |
| `bioetl.domain.transformations.quality` | `retain_canonical_owner_module` | `src/bioetl/domain/transformations/quality.py` |
| `bioetl.infrastructure.export.export_catalog_adapter` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/export/export_catalog_adapter.py` |
| `bioetl.infrastructure.export.export_writer_adapter` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/export/export_writer_adapter.py` |
| `bioetl.infrastructure.storage.bronze.metadata_builders` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/storage/bronze/metadata_builders.py` |
| `bioetl.infrastructure.storage.silver.arrow_mixin` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/storage/silver/arrow_mixin.py` |
| `bioetl.infrastructure.storage.silver.dtos` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/storage/silver/dtos.py` |
| `bioetl.infrastructure.storage.silver.operations.metadata_finalization_support` | `retain_canonical_owner_module` | `src/bioetl/infrastructure/storage/silver/operations/metadata_finalization_support.py` |
| `bioetl.interfaces.cli.commands.archive` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/archive.py` |
| `bioetl.interfaces.cli.commands.cleanup` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/cleanup.py` |
| `bioetl.interfaces.cli.commands.config_dq` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/config_dq.py` |
| `bioetl.interfaces.cli.commands.debug` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/debug.py` |
| `bioetl.interfaces.cli.commands.lock` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/lock.py` |
| `bioetl.interfaces.cli.commands.vacuum` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/vacuum.py` |
| `bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle` | `retain_dynamic_entrypoint` | `src/bioetl/interfaces/cli/commands/domains/maintenance/control_plane_lifecycle.py` |
