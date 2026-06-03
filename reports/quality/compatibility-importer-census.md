# Compatibility Importer Census

- snapshot_date: 2026-06-02
- retained_entrypoint_count: 14
- removed_compatibility_surface_count: 23
- removed_compatibility_surfaces_with_src_importers: 0
- removed_compatibility_surfaces_with_test_importers: 0
- removed_compatibility_surfaces_still_present: 0
- twin_pair_count: 1
- tracked_twin_family_count: 0
- config_root_symbol_count: 3
- config_root_src_importer_count: 0
- retained_public_export_facade_count: 4
- retained_public_export_facades_with_duplicate_exports: 0
- retained_public_export_facades_with_resolution_conflicts: 0
- purpose: measure sanctioned public seams and underscore/public twin usage

## Retained Entrypoints

| Path | src importers | test importers |
| --- | ---: | ---: |
| `src/bioetl/interfaces/cli/commands/run.py` | 0 | 2 |
| `src/bioetl/interfaces/cli/commands/run_all.py` | 1 | 5 |
| `src/bioetl/interfaces/cli/commands/run_composite.py` | 1 | 1 |
| `src/bioetl/interfaces/cli/commands/health.py` | 4 | 1 |
| `src/bioetl/interfaces/cli/commands/diagnostics.py` | 1 | 2 |
| `src/bioetl/interfaces/cli/commands/quarantine.py` | 1 | 0 |
| `src/bioetl/interfaces/cli/commands/maintenance.py` | 0 | 0 |
| `src/bioetl/composition/entrypoints.py` | 0 | 3 |
| `src/bioetl/composition/health_api.py` | 2 | 2 |
| `src/bioetl/composition/maintenance_api.py` | 1 | 1 |
| `src/bioetl/infrastructure/config/__init__.py` | 0 | 2 |
| `src/bioetl/domain/composite/config.py` | 81 | 34 |
| `src/bioetl/domain/value_objects/activity_values.py` | 0 | 1 |
| `src/bioetl/application/composite/merger.py` | 5 | 4 |

## Retained Public Export Facades

| Path | Public exports | Lazy exports | Duplicate exports | Resolution conflicts |
| --- | ---: | ---: | --- | --- |
| `src/bioetl/composition/entrypoints.py` | 15 | 15 | none | none |
| `src/bioetl/composition/health_api.py` | 8 | 3 | none | none |
| `src/bioetl/composition/maintenance_api.py` | 8 | 8 | none | none |
| `src/bioetl/infrastructure/config/__init__.py` | 18 | 5 | none | none |

## Removed Compatibility Surfaces

| Module | Path exists | src importers | test importers | Canonical target |
| --- | --- | ---: | ---: | --- |
| `bioetl.application.services.control_plane.historical_replay_certification_service` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_certification_service` |
| `bioetl.application.services.control_plane.historical_replay_closure_models` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_closure_models` |
| `bioetl.application.services.control_plane.historical_replay_closure_policy` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_closure_policy` |
| `bioetl.application.services.control_plane.historical_replay_closure_service` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_closure_service` |
| `bioetl.application.services.control_plane.historical_replay_corpus_models` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_corpus_models` |
| `bioetl.application.services.control_plane.historical_replay_corpus_policy` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_corpus_policy` |
| `bioetl.application.services.control_plane.historical_replay_corpus_service` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_corpus_service` |
| `bioetl.application.services.control_plane.historical_replay_universe_policy` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_universe_policy` |
| `bioetl.application.services.control_plane.historical_replay_universe_service` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.historical_universe_service` |
| `bioetl.application.services.control_plane.replay_bundle_descriptor_service` | no | 0 | 0 | `bioetl.application.services.control_plane.replay.bundle_descriptor_service` |
| `bioetl.application.services.control_plane.run_manifest_diagnostics` | no | 0 | 0 | `bioetl.application.services.control_plane.manifest.diagnostics` |
| `bioetl.application.services.control_plane.run_manifest_inspection_service` | no | 0 | 0 | `bioetl.application.services.control_plane.manifest.inspection_service` |
| `bioetl.application.services.control_plane.run_manifest_replay_taxonomy` | no | 0 | 0 | `bioetl.application.services.control_plane.manifest.replay_taxonomy` |
| `bioetl.application.services.control_plane.workflow_execution_preparation` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.execution_preparation` |
| `bioetl.application.services.control_plane.workflow_execution_recording` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.execution_recording` |
| `bioetl.application.services.control_plane.workflow_execution_service` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.execution_service` |
| `bioetl.application.services.control_plane.workflow_inspection_service` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.inspection_service` |
| `bioetl.application.services.control_plane.workflow_ledger_service` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.ledger_service` |
| `bioetl.application.services.control_plane.workflow_manifest_models` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.manifest_models` |
| `bioetl.application.services.control_plane.workflow_manifest_service` | no | 0 | 0 | `bioetl.application.services.control_plane.workflow.manifest_service` |
| `bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter` | no | 0 | 0 | `bioetl.domain.ports.storage.metadata.MetadataCoordinatorPort` |
| `bioetl.application.services.checkpoint_compatibility_service_v2` | no | 0 | 0 | `bioetl.application.services.checkpoint_compatibility_service` |
| `bioetl.domain.normalization.legacy_fingerprints` | no | 0 | 0 | `bioetl.domain.normalization.fingerprints` |

## Twin Modules

| Public module | Public src | Private src |
| --- | ---: | ---: |
| `bioetl.composition.lazy_exports` | 1 | 9 |

## Tracked Twin Family Ratchet

- inventory_source: `configs/quality/compatibility_twin_module_ratchet.yaml`

| Family | Canonical first-party module | Current public src | Current private src | Max public src | Max private src |
| --- | --- | ---: | ---: | ---: | ---: |

## Infrastructure Config Root Facade

- inventory_source: `configs/quality/infrastructure_config_root_facade_inventory.yaml`
- target_module: `bioetl.infrastructure.config`
- new_src_import_policy: `external_only_zero_first_party_growth`

| Symbol | Current src importers | Max src importers | Canonical target |
| --- | ---: | ---: | --- |
| `Settings` | 0 | 0 | `bioetl.infrastructure.config._base.Settings` |
| `get_settings` | 0 | 0 | `bioetl.infrastructure.config._base.get_settings` |
| `load_pipeline_contract_policy` | 0 | 0 | `bioetl.infrastructure.config.contract_policy_loader.load_pipeline_contract_policy` |
