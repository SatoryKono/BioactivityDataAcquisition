# FINDINGS — CR-FULL residual (de-duped)

- Generated: 2026-08-06T07:40Z
- Epic: #7688 · Task: #7696
- Open residual clusters before de-dupe: 268
- Canonical kept: 220
- Duplicates closed/identified: 48 (dry-run)
- Agent NDJSON severity totals A–D: {'major': 736, 'trivial': 457, 'minor': 253, 'critical': 22} (sum=1468)

## Columns

| id | sev | wave | path | findings | action | issue |
| --- | --- | --- | --- | ---: | --- | ---: |
| CR-A-7738 | critical | A | `src/bioetl/composition/bootstrap/runtime` | 34 | P0 | #7738 |
| CR-A-7750 | critical | A | `src/bioetl/application/services/control_plane` | 73 | P0 | #7750 |
| CR-A-7770 | critical | A | `src/bioetl/application/core/base_transformer` | 4 | P0 | #7770 |
| CR-A-7779 | critical | A | `src/bioetl/application/core/batch_checkpoint_recovery_service.py` | 3 | P0 | #7779 |
| CR-A-7793 | critical | A | `src/bioetl/interfaces/http/health_server_http_mixin.py` | 2 | P0 | #7793 |
| CR-A-7809 | critical | A | `src/bioetl/infrastructure/adapters/http` | 2 | P0 | #7809 |
| CR-A-7821 | critical | A | `src/bioetl/infrastructure/adapters/crossref` | 10 | P0 | #7821 |
| CR-A-7840 | critical | A | `src/bioetl/application/core/batch_transformer_streaming.py` | 1 | P0 | #7840 |
| CR-A-7887 | critical | A | `src/bioetl/interfaces/http/run_report_ops.py` | 2 | P0 | #7887 |
| CR-B-7972 | critical | B | `src/bioetl/application/pipelines/crossref` | 9 | P0 | #7972 |
| CR-B-7993 | critical | B | `src/bioetl/infrastructure/storage/metadata` | 3 | P0 | #7993 |
| CR-D-8030 | critical | D | `tests/security` | 5 | P0 | #8030 |
| CR-A-7739 | major | A | `src/bioetl/composition/factories/pipeline` | 17 | P1 | #7739 |
| CR-A-7740 | major | A | `src/bioetl/composition/factories/services` | 16 | P1 | #7740 |
| CR-A-7741 | major | A | `src/bioetl/composition/factories/storage` | 12 | P1 | #7741 |
| CR-A-7742 | major | A | `src/bioetl/composition/factories/pipeline_support` | 8 | P1 | #7742 |
| CR-A-7743 | major | A | `src/bioetl/composition/bootstrap/cli` | 6 | P1 | #7743 |
| CR-A-7744 | major | A | `src/bioetl/composition/factories/datasource` | 6 | P1 | #7744 |
| CR-A-7745 | major | A | `src/bioetl/composition/bootstrap/assembly` | 5 | P1 | #7745 |
| CR-A-7746 | major | A | `src/bioetl/interfaces/http/control_plane_identity` | 5 | P1 | #7746 |
| CR-A-7747 | major | A | `src/bioetl/composition/factories/dq` | 3 | P1 | #7747 |
| CR-A-7748 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py` | 1 | P1 | #7748 |
| CR-A-7749 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_data_roots.py` | 3 | P1 | #7749 |
| CR-A-7751 | major | A | `src/bioetl/composition/runtime_builders/_snapshot_mapping_support.py` | 3 | P1 | #7751 |
| CR-A-7752 | major | A | `src/bioetl/composition/services/versioning.py` | 3 | P1 | #7752 |
| CR-A-7753 | major | A | `src/bioetl/composition/_workflow_services.py` | 2 | P1 | #7753 |
| CR-A-7754 | major | A | `src/bioetl/composition/builders.py` | 2 | P1 | #7754 |
| CR-A-7755 | major | A | `src/bioetl/composition/factories/_observability_wiring.py` | 2 | P1 | #7755 |
| CR-A-7757 | major | A | `src/bioetl/composition/providers/_config_helpers.py` | 2 | P1 | #7757 |
| CR-A-7758 | major | A | `src/bioetl/composition/providers/_registration_contracts.py` | 2 | P1 | #7758 |
| CR-A-7759 | major | A | `src/bioetl/composition/providers/registration.py` | 2 | P1 | #7759 |
| CR-A-7760 | major | A | `src/bioetl/application/core/postrun` | 3 | P1 | #7760 |
| CR-A-7761 | major | A | `src/bioetl/application/core/_batch_write_support.py` | 2 | P1 | #7761 |
| CR-A-7762 | major | A | `src/bioetl/application/core/publication_term_extraction_mixin.py` | 2 | P1 | #7762 |
| CR-A-7763 | major | A | `src/bioetl/application/core/wiring` | 2 | P1 | #7763 |
| CR-A-7765 | major | A | `src/bioetl/composition/runtime_builders/_exact_replay_cached_bronze_context.py` | 1 | P1 | #7765 |
| CR-A-7766 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_builder_policy.py` | 1 | P1 | #7766 |
| CR-A-7768 | major | A | `src/bioetl/composition/runtime_builders/config_access.py` | 2 | P1 | #7768 |
| CR-A-7769 | major | A | `src/bioetl/composition/runtime_builders/input_snapshot_resolution.py` | 2 | P1 | #7769 |
| CR-A-7771 | major | A | `src/bioetl/application/core/_batch_writer_gold_support.py` | 2 | P1 | #7771 |
| CR-A-7772 | major | A | `src/bioetl/application/core/_quarantine_metrics_support.py` | 2 | P1 | #7772 |
| CR-A-7773 | major | A | `src/bioetl/application/core/_record_normalization_mapping.py` | 2 | P1 | #7773 |
| CR-A-7774 | major | A | `src/bioetl/application/core/batch_executor_dq_helpers.py` | 2 | P1 | #7774 |
| CR-A-7775 | major | A | `src/bioetl/application/core/batch_executor_dq_mixin.py` | 2 | P1 | #7775 |
| CR-A-7776 | major | A | `src/bioetl/application/core/batch_executor_helpers.py` | 2 | P1 | #7776 |
| CR-A-7777 | major | A | `src/bioetl/application/core/entity_id.py` | 2 | P1 | #7777 |
| CR-A-7778 | major | A | `src/bioetl/application/core/batch_execution` | 5 | P1 | #7778 |
| CR-A-7780 | major | A | `src/bioetl/application/core/batch_writer_columns_mixin.py` | 2 | P1 | #7780 |
| CR-A-7781 | major | A | `src/bioetl/application/core/batch_writer_io_mixin.py` | 2 | P1 | #7781 |
| CR-A-7782 | major | A | `src/bioetl/application/core/batch_writer_tracing_mixin.py` | 2 | P1 | #7782 |
| CR-A-7783 | major | A | `src/bioetl/application/core/lifecycle` | 2 | P1 | #7783 |
| CR-A-7784 | major | A | `src/bioetl/application/core/pre_silver_finalization_flow.py` | 2 | P1 | #7784 |
| CR-A-7785 | major | A | `src/bioetl/application/core/preflight` | 2 | P1 | #7785 |
| CR-A-7786 | major | A | `src/bioetl/application/core/runner.py` | 2 | P1 | #7786 |
| CR-A-7787 | major | A | `src/bioetl/application/core/subcellular_fraction_support.py` | 2 | P1 | #7787 |
| CR-A-7791 | major | A | `src/bioetl/composition/services/effective_config_serializer.py` | 2 | P1 | #7791 |
| CR-A-7792 | major | A | `src/bioetl/interfaces/http/health_server.py` | 2 | P1 | #7792 |
| CR-A-7794 | major | A | `src/bioetl/interfaces/http/health_server_routing_mixin.py` | 2 | P1 | #7794 |
| CR-A-7795 | major | A | `src/bioetl/application/core/_base_transformer_structural_support.py` | 1 | P1 | #7795 |
| CR-A-7796 | major | A | `src/bioetl/application/core/_batch_processing_layer_write_support.py` | 1 | P1 | #7796 |
| CR-A-7797 | major | A | `src/bioetl/application/core/_fetch_forwarding.py` | 1 | P1 | #7797 |
| CR-A-7798 | major | A | `src/bioetl/application/core/_filtered_data_source_fetch_support.py` | 1 | P1 | #7798 |
| CR-A-7799 | major | A | `src/bioetl/application/core/_filtered_data_source_support.py` | 1 | P1 | #7799 |
| CR-A-7800 | major | A | `src/bioetl/application/core/_quarantine_support.py` | 1 | P1 | #7800 |
| CR-A-7801 | major | A | `src/bioetl/application/core/_quarantine_write_support.py` | 1 | P1 | #7801 |
| CR-A-7802 | major | A | `src/bioetl/application/core/_record_normalization_hash_support.py` | 1 | P1 | #7802 |
| CR-A-7803 | major | A | `src/bioetl/application/core/_record_processor_span_support.py` | 1 | P1 | #7803 |
| CR-A-7805 | major | A | `src/bioetl/infrastructure/adapters/uniprot` | 4 | P1 | #7805 |
| CR-A-7810 | major | A | `src/bioetl/infrastructure/adapters/openalex` | 2 | P1 | #7810 |
| CR-A-7811 | major | A | `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py` | 1 | P1 | #7811 |
| CR-A-7812 | major | A | `src/bioetl/application/core/base_transformer_execution_mixin.py` | 1 | P1 | #7812 |
| CR-A-7813 | major | A | `src/bioetl/application/core/batch_executor_loop_progress.py` | 1 | P1 | #7813 |
| CR-A-7814 | major | A | `src/bioetl/application/core/batch_executor_runtime_state.py` | 1 | P1 | #7814 |
| CR-A-7815 | major | A | `src/bioetl/application/core/batch_memory_manager.py` | 1 | P1 | #7815 |
| CR-A-7816 | major | A | `src/bioetl/application/core/batch_metrics.py` | 1 | P1 | #7816 |
| CR-A-7817 | major | A | `src/bioetl/application/core/batch_processing_runtime.py` | 1 | P1 | #7817 |
| CR-A-7818 | major | A | `src/bioetl/application/core/batch_processing_service.py` | 1 | P1 | #7818 |
| CR-A-7819 | major | A | `src/bioetl/application/core/batch_processing_support.py` | 1 | P1 | #7819 |
| CR-A-7820 | major | A | `src/bioetl/application/core/batch_progress_service.py` | 1 | P1 | #7820 |
| CR-A-7822 | major | A | `src/bioetl/infrastructure/adapters/common` | 9 | P1 | #7822 |
| CR-A-7823 | major | A | `src/bioetl/infrastructure/adapters/decorators` | 7 | P1 | #7823 |
| CR-A-7824 | major | A | `src/bioetl/infrastructure/adapters/pubchem` | 7 | P1 | #7824 |
| CR-A-7825 | major | A | `src/bioetl/infrastructure/adapters/chembl` | 6 | P1 | #7825 |
| CR-A-7826 | major | A | `src/bioetl/infrastructure/adapters/pubmed` | 5 | P1 | #7826 |
| CR-A-7827 | major | A | `src/bioetl/infrastructure/adapters/semanticscholar` | 3 | P1 | #7827 |
| CR-A-7828 | major | A | `src/bioetl/infrastructure/adapters/_error_handling_support.py` | 2 | P1 | #7828 |
| CR-A-7831 | major | A | `src/bioetl/infrastructure/adapters/base.py` | 2 | P1 | #7831 |
| CR-A-7832 | major | A | `src/bioetl/application/core/batch_runtime_failure_policy.py` | 1 | P1 | #7832 |
| CR-A-7833 | major | A | `src/bioetl/application/core/batch_transformer.py` | 1 | P1 | #7833 |
| CR-A-7834 | major | A | `src/bioetl/application/core/batch_transformer_attempt_success.py` | 1 | P1 | #7834 |
| CR-A-7835 | major | A | `src/bioetl/application/core/batch_transformer_attempts.py` | 1 | P1 | #7835 |
| CR-A-7836 | major | A | `src/bioetl/application/core/batch_transformer_dq_thresholds.py` | 1 | P1 | #7836 |
| CR-A-7837 | major | A | `src/bioetl/application/core/batch_transformer_finalization.py` | 1 | P1 | #7837 |
| CR-A-7838 | major | A | `src/bioetl/application/core/batch_transformer_quarantine.py` | 1 | P1 | #7838 |
| CR-A-7839 | major | A | `src/bioetl/application/core/batch_transformer_state.py` | 1 | P1 | #7839 |
| CR-A-7841 | major | A | `src/bioetl/application/core/config.py` | 1 | P1 | #7841 |
| CR-A-7842 | major | A | `src/bioetl/application/core/data_sources` | 1 | P1 | #7842 |
| CR-A-7843 | major | A | `src/bioetl/application/core/normalization_fallbacks.py` | 1 | P1 | #7843 |
| CR-A-7844 | major | A | `src/bioetl/application/core/pipeline_services.py` | 1 | P1 | #7844 |
| CR-A-7845 | major | A | `src/bioetl/application/core/publication_term_filtering_mixin.py` | 1 | P1 | #7845 |
| CR-A-7846 | major | A | `src/bioetl/application/core/publication_term_runtime.py` | 1 | P1 | #7846 |
| CR-A-7847 | major | A | `src/bioetl/application/core/record_processor.py` | 1 | P1 | #7847 |
| CR-A-7848 | major | A | `src/bioetl/application/core/runner_flow_metrics.py` | 1 | P1 | #7848 |
| CR-A-7849 | major | A | `src/bioetl/composition/_pipeline_execution.py` | 1 | P1 | #7849 |
| CR-A-7850 | major | A | `src/bioetl/composition/_service_protocols.py` | 1 | P1 | #7850 |
| CR-A-7852 | major | A | `src/bioetl/interfaces/cli/commands` | 5 | P1 | #7852 |
| CR-A-7853 | major | A | `src/bioetl/interfaces/cli/__main__.py` | 2 | P1 | #7853 |
| CR-A-7854 | major | A | `src/bioetl/composition/_services.py` | 1 | P1 | #7854 |
| CR-A-7855 | major | A | `src/bioetl/composition/bootstrap/control_plane_store_builders.py` | 1 | P1 | #7855 |
| CR-A-7856 | major | A | `src/bioetl/composition/bootstrap_contexts.py` | 1 | P1 | #7856 |
| CR-A-7857 | major | A | `src/bioetl/composition/config_catalog.py` | 1 | P1 | #7857 |
| CR-A-7858 | major | A | `src/bioetl/composition/factories/__init__.py` | 1 | P1 | #7858 |
| CR-A-7859 | major | A | `src/bioetl/composition/observability.py` | 1 | P1 | #7859 |
| CR-A-7860 | major | A | `src/bioetl/composition/occurrence_identity.py` | 1 | P1 | #7860 |
| CR-A-7861 | major | A | `src/bioetl/composition/pipeline_runner_request.py` | 1 | P1 | #7861 |
| CR-A-7864 | major | A | `src/bioetl/composition/providers/_creation.py` | 1 | P1 | #7864 |
| CR-A-7865 | major | A | `src/bioetl/composition/providers/_default_registry.py` | 1 | P1 | #7865 |
| CR-A-7866 | major | A | `src/bioetl/composition/providers/_loading.py` | 1 | P1 | #7866 |
| CR-A-7867 | major | A | `src/bioetl/composition/providers/_registration_biblio_adapters.py` | 1 | P1 | #7867 |
| CR-A-7869 | major | A | `src/bioetl/composition/providers/_registration_biblio_profiles.py` | 1 | P1 | #7869 |
| CR-A-7870 | major | A | `src/bioetl/composition/providers/_registry_resolution.py` | 1 | P1 | #7870 |
| CR-A-7871 | major | A | `src/bioetl/composition/providers/decorators.py` | 1 | P1 | #7871 |
| CR-A-7872 | major | A | `src/bioetl/composition/providers/registration_bio.py` | 1 | P1 | #7872 |
| CR-A-7873 | major | A | `src/bioetl/composition/runtime_builders/_context_field_binding.py` | 1 | P1 | #7873 |
| CR-A-7875 | major | A | `src/bioetl/composition/runtime_builders/_effective_config_secret_support.py` | 1 | P1 | #7875 |
| CR-A-7878 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_context_updates.py` | 1 | P1 | #7878 |
| CR-A-7880 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_identity_ref_values.py` | 1 | P1 | #7880 |
| CR-A-7881 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_sink_policy.py` | 1 | P1 | #7881 |
| CR-A-7882 | major | A | `src/bioetl/composition/runtime_builders/_run_manifest_snapshot_support.py` | 1 | P1 | #7882 |
| CR-A-7883 | major | A | `src/bioetl/composition/runtime_builders/_runner_control_plane_policy.py` | 1 | P1 | #7883 |
| CR-A-7884 | major | A | `src/bioetl/composition/runtime_builders/_runner_input_preparation.py` | 1 | P1 | #7884 |
| CR-A-7885 | major | A | `src/bioetl/composition/runtime_builders/_runtime_launch_context_fields.py` | 1 | P1 | #7885 |
| CR-A-7886 | major | A | `src/bioetl/composition/runtime_builders/cached_bronze_snapshot_support.py` | 1 | P1 | #7886 |
| CR-A-7888 | major | A | `src/bioetl/composition/runtime_builders/inputs_runtime_helpers.py` | 1 | P1 | #7888 |
| CR-A-7889 | major | A | `src/bioetl/composition/runtime_builders/ledger_collaborator.py` | 1 | P1 | #7889 |
| CR-A-7890 | major | A | `src/bioetl/composition/runtime_builders/run_manifest_builder.py` | 1 | P1 | #7890 |
| CR-A-7891 | major | A | `src/bioetl/composition/runtime_builders/run_manifest_contract_identity.py` | 1 | P1 | #7891 |
| CR-A-7892 | major | A | `src/bioetl/composition/runtime_builders/run_manifest_support.py` | 1 | P1 | #7892 |
| CR-A-7893 | major | A | `src/bioetl/composition/runtime_builders/runner_control_plane_assembly.py` | 1 | P1 | #7893 |
| CR-A-7894 | major | A | `src/bioetl/composition/runtime_builders/runner_inputs.py` | 1 | P1 | #7894 |
| CR-A-7895 | major | A | `src/bioetl/interfaces/http/_health_server_identity_routing_support.py` | 1 | P1 | #7895 |
| CR-A-7896 | major | A | `src/bioetl/infrastructure/adapters/_cached_bronze_support.py` | 1 | P1 | #7896 |
| CR-A-7897 | major | A | `src/bioetl/infrastructure/adapters/_error_handler_ops.py` | 1 | P1 | #7897 |
| CR-A-7898 | major | A | `src/bioetl/infrastructure/adapters/_health_check_observability.py` | 1 | P1 | #7898 |
| CR-A-7899 | major | A | `src/bioetl/infrastructure/adapters/base_metrics.py` | 1 | P1 | #7899 |
| CR-A-7900 | major | A | `src/bioetl/infrastructure/adapters/circuit_breaker_contract.py` | 1 | P1 | #7900 |
| CR-A-7901 | major | A | `src/bioetl/infrastructure/adapters/health_check_mixin.py` | 1 | P1 | #7901 |
| CR-A-7902 | major | A | `src/bioetl/infrastructure/adapters/input` | 1 | P1 | #7902 |
| CR-A-7903 | major | A | `src/bioetl/domain/ports/observability` | 2 | P1 | #7903 |
| CR-A-7904 | major | A | `src/bioetl/domain/ports/control_plane` | 1 | P1 | #7904 |
| CR-A-7905 | major | A | `src/bioetl/domain/ports/delta_reader.py` | 1 | P1 | #7905 |
| CR-A-7906 | major | A | `src/bioetl/domain/ports/export.py` | 1 | P1 | #7906 |
| CR-A-7907 | major | A | `src/bioetl/domain/ports/health_check.py` | 1 | P1 | #7907 |
| CR-A-7908 | major | A | `src/bioetl/infrastructure/adapters/sync_base.py` | 1 | P1 | #7908 |
| CR-A-7909 | major | A | `src/bioetl/interfaces/cli/__init__.py` | 1 | P1 | #7909 |
| CR-A-7910 | major | A | `src/bioetl/interfaces/cli/main.py` | 1 | P1 | #7910 |
| CR-A-7911 | major | A | `src/bioetl/domain/ports/runtime` | 3 | P1 | #7911 |
| CR-A-7912 | major | A | `src/bioetl/domain/ports/noop` | 2 | P1 | #7912 |
| CR-A-7913 | major | A | `src/bioetl/domain/ports/quality` | 2 | P1 | #7913 |
| CR-A-7914 | major | A | `src/bioetl/domain/ports/storage` | 2 | P1 | #7914 |
| CR-A-7915 | major | A | `src/bioetl/domain/ports/storage_maintenance.py` | 2 | P1 | #7915 |
| CR-A-7916 | major | A | `src/bioetl/domain/ports/workflow_foreign_key_reconciliation.py` | 2 | P1 | #7916 |
| CR-A-7917 | major | A | `src/bioetl/domain/ports/__init__.py` | 1 | P1 | #7917 |
| CR-A-7918 | major | A | `src/bioetl/domain/ports/adr.py` | 1 | P1 | #7918 |
| CR-A-7920 | major | A | `src/bioetl/domain/ports/audit.py` | 1 | P1 | #7920 |
| CR-A-7922 | major | A | `src/bioetl/domain/ports/data_source.py` | 1 | P1 | #7922 |
| CR-A-7929 | major | A | `src/bioetl/domain/contracts/gold` | 8 | P1 | #7929 |
| CR-A-7930 | major | A | `src/bioetl/interfaces/http/_health_server_checkpoint_freshness_payloads.py` | 1 | P1 | #7930 |
| CR-A-7931 | major | A | `src/bioetl/interfaces/http/_health_server_control_plane_scope.py` | 1 | P1 | #7931 |
| CR-A-7932 | major | A | `src/bioetl/interfaces/http/_health_server_quarantine_routing.py` | 1 | P1 | #7932 |
| CR-A-7933 | major | A | `src/bioetl/interfaces/http/_pipeline_run_report_table.py` | 1 | P1 | #7933 |
| CR-A-7934 | major | A | `src/bioetl/interfaces/http/health_server_state_mixin.py` | 1 | P1 | #7934 |
| CR-A-7935 | major | A | `src/bioetl/interfaces/http/processed_records_table.py` | 1 | P1 | #7935 |
| CR-B-7962 | major | B | `src/bioetl/application/pipelines/chembl` | 8 | P1 | #7962 |
| CR-B-7973 | major | B | `src/bioetl/application/pipelines/common` | 7 | P1 | #7973 |
| CR-B-7974 | major | B | `src/bioetl/application/pipelines/pubmed` | 6 | P1 | #7974 |
| CR-B-7975 | major | B | `src/bioetl/application/pipelines/uniprot` | 6 | P1 | #7975 |
| CR-B-7982 | major | B | `src/bioetl/application/pipelines/pubchem` | 3 | P1 | #7982 |
| CR-B-7983 | major | B | `src/bioetl/application/pipelines/semanticscholar` | 3 | P1 | #7983 |
| CR-B-7984 | major | B | `src/bioetl/application/pipelines/openalex` | 2 | P1 | #7984 |
| CR-B-7985 | major | B | `src/bioetl/application/pipelines/generic.py` | 1 | P1 | #7985 |
| CR-B-7986 | major | B | `src/bioetl/infrastructure/storage/bronze` | 4 | P1 | #7986 |
| CR-B-7987 | major | B | `src/bioetl/infrastructure/storage/support` | 3 | P1 | #7987 |
| CR-B-7988 | major | B | `src/bioetl/infrastructure/storage/gold` | 2 | P1 | #7988 |
| CR-B-7989 | major | B | `src/bioetl/infrastructure/storage/atomic.py` | 1 | P1 | #7989 |
| CR-B-7990 | major | B | `src/bioetl/infrastructure/storage/bronze_write_result_helpers.py` | 1 | P1 | #7990 |
| CR-B-7991 | major | B | `src/bioetl/infrastructure/storage/silver` | 1 | P1 | #7991 |
| CR-B-7994 | major | B | `src/bioetl/infrastructure/storage/delta` | 2 | P1 | #7994 |
| CR-B-7995 | major | B | `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation.py` | 1 | P1 | #7995 |
| CR-B-7997 | major | B | `src/bioetl/infrastructure/storage/base_delta_writer_access.py` | 1 | P1 | #7997 |
| CR-B-7998 | major | B | `src/bioetl/infrastructure/storage/bronze_writer.py` | 1 | P1 | #7998 |
| CR-B-7999 | major | B | `src/bioetl/infrastructure/storage/delta_reader.py` | 1 | P1 | #7999 |
| CR-B-8000 | major | B | `src/bioetl/infrastructure/storage/gold_writer.py` | 1 | P1 | #8000 |
| CR-B-8001 | major | B | `src/bioetl/infrastructure/storage/lineage_persistence.py` | 1 | P1 | #8001 |
| CR-B-8002 | major | B | `src/bioetl/infrastructure/storage/metadata_artifact_details.py` | 1 | P1 | #8002 |
| CR-B-8003 | major | B | `src/bioetl/infrastructure/storage/metadata_writer.py` | 1 | P1 | #8003 |
| CR-B-8004 | major | B | `src/bioetl/infrastructure/storage/metadata_writer_helpers.py` | 1 | P1 | #8004 |
| CR-B-8005 | major | B | `src/bioetl/infrastructure/storage/workflow_row_reconciliation.py` | 1 | P1 | #8005 |
| CR-B-8006 | major | B | `configs/quality` | 8 | P1 | #8006 |
| CR-C-8007 | major | C | `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py` | 2 | P1 | #8007 |
| CR-C-8008 | major | C | `src/bioetl/infrastructure/observability/_metrics_gateway_publication.py` | 1 | P1 | #8008 |
| CR-C-8009 | major | C | `src/bioetl/infrastructure/observability/_metrics_server_state.py` | 1 | P1 | #8009 |
| CR-C-8010 | major | C | `src/bioetl/infrastructure/observability/debug_adapters.py` | 1 | P1 | #8010 |
| CR-C-8011 | major | C | `src/bioetl/infrastructure/observability/metrics_collector.py` | 1 | P1 | #8011 |
| CR-C-8012 | major | C | `src/bioetl/infrastructure/observability/anomaly` | 3 | P1 | #8012 |
| CR-C-8013 | major | C | `src/bioetl/infrastructure/observability/_metrics_defs_adapter.py` | 2 | P1 | #8013 |
| CR-C-8014 | major | C | `src/bioetl/infrastructure/observability/logging_config.py` | 2 | P1 | #8014 |
| CR-C-8015 | major | C | `src/bioetl/infrastructure/observability/prometheus_metric_registries.py` | 1 | P1 | #8015 |
| CR-C-8016 | major | C | `src/bioetl/infrastructure/observability/tracing.py` | 2 | P1 | #8016 |
| CR-C-8017 | major | C | `src/bioetl/infrastructure/observability/__init__.py` | 1 | P1 | #8017 |
| CR-C-8018 | major | C | `src/bioetl/infrastructure/observability/_metrics_defs_core.py` | 1 | P1 | #8018 |
| CR-C-8019 | major | C | `src/bioetl/infrastructure/observability/_metrics_defs_pipeline_checkpoint.py` | 1 | P1 | #8019 |
| CR-C-8020 | major | C | `src/bioetl/infrastructure/observability/_metrics_defs_storage.py` | 1 | P1 | #8020 |
| CR-C-8023 | major | C | `src/bioetl/infrastructure/observability/circuit_breaker_mapping.py` | 1 | P1 | #8023 |
| CR-C-8024 | major | C | `src/bioetl/infrastructure/observability/logging.py` | 1 | P1 | #8024 |
| CR-C-8025 | major | C | `src/bioetl/infrastructure/observability/logging_helpers.py` | 1 | P1 | #8025 |
| CR-C-8026 | major | C | `src/bioetl/infrastructure/observability/metrics_definitions.py` | 1 | P1 | #8026 |
| CR-C-8027 | major | C | `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py` | 1 | P1 | #8027 |
| CR-C-8028 | major | C | `src/bioetl/infrastructure/observability/server.py` | 1 | P1 | #8028 |
| CR-C-8029 | major | C | `src/bioetl/infrastructure/observability/unified_logger.py` | 1 | P1 | #8029 |

## Duplicates (closed → canonical)

| duplicate | canonical | path | reason |
| ---: | ---: | --- | --- |
| #7919 | #7911 | `src/bioetl/domain/ports/runtime` | A/major → A/major |
| #7921 | #7912 | `src/bioetl/domain/ports/noop` | A/major → A/major |
| #7923 | #7913 | `src/bioetl/domain/ports/quality` | A/major → A/major |
| #7924 | #7914 | `src/bioetl/domain/ports/storage` | A/major → A/major |
| #7925 | #7915 | `src/bioetl/domain/ports/storage_maintenance.py` | A/major → A/major |
| #7926 | #7916 | `src/bioetl/domain/ports/workflow_foreign_key_reconciliation.py` | A/major → A/major |
| #7927 | #7917 | `src/bioetl/domain/ports/__init__.py` | A/major → A/major |
| #7928 | #7918 | `src/bioetl/domain/ports/adr.py` | A/major → A/major |
| #7936 | #7779 | `src/bioetl/application/core/batch_checkpoint_recovery_service.py` | A/critical → A/critical |
| #7937 | #7748 | `src/bioetl/composition/runtime_builders/_run_manifest_creation_support.py` | A/major → A/major |
| #7938 | #7749 | `src/bioetl/composition/runtime_builders/_run_manifest_data_roots.py` | A/major → A/major |
| #7939 | #7751 | `src/bioetl/composition/runtime_builders/_snapshot_mapping_support.py` | A/major → A/major |
| #7940 | #7895 | `src/bioetl/interfaces/http/_health_server_identity_routing_support.py` | A/major → A/major |
| #7941 | #7761 | `src/bioetl/application/core/_batch_write_support.py` | A/major → A/major |
| #7942 | #7771 | `src/bioetl/application/core/_batch_writer_gold_support.py` | A/major → A/major |
| #7943 | #7772 | `src/bioetl/application/core/_quarantine_metrics_support.py` | A/major → A/major |
| #7944 | #7773 | `src/bioetl/application/core/_record_normalization_mapping.py` | A/major → A/major |
| #7945 | #7774 | `src/bioetl/application/core/batch_executor_dq_helpers.py` | A/major → A/major |
| #7947 | #7775 | `src/bioetl/application/core/batch_executor_dq_mixin.py` | A/major → A/major |
| #7948 | #7776 | `src/bioetl/application/core/batch_executor_helpers.py` | A/major → A/major |
| #7949 | #7780 | `src/bioetl/application/core/batch_writer_columns_mixin.py` | A/major → A/major |
| #7950 | #7781 | `src/bioetl/application/core/batch_writer_io_mixin.py` | A/major → A/major |
| #7951 | #7782 | `src/bioetl/application/core/batch_writer_tracing_mixin.py` | A/major → A/major |
| #7952 | #7750 | `src/bioetl/application/services/control_plane` | B/critical → A/critical |
| #7953 | #7738 | `src/bioetl/composition/bootstrap/runtime` | B/critical → A/critical |
| #7954 | #7852 | `src/bioetl/interfaces/cli/commands` | B/major → A/major |
| #7955 | #7739 | `src/bioetl/composition/factories/pipeline` | B/major → A/major |
| #7956 | #7740 | `src/bioetl/composition/factories/services` | B/major → A/major |
| #7957 | #7741 | `src/bioetl/composition/factories/storage` | B/major → A/major |
| #7958 | #7821 | `src/bioetl/infrastructure/adapters/crossref` | B/critical → A/critical |
| #7959 | #7810 | `src/bioetl/infrastructure/adapters/openalex` | B/major → A/major |
| #7960 | #7805 | `src/bioetl/infrastructure/adapters/uniprot` | B/major → A/major |
| #7961 | #7822 | `src/bioetl/infrastructure/adapters/common` | B/major → A/major |
| #7963 | #7742 | `src/bioetl/composition/factories/pipeline_support` | B/major → A/major |
| #7964 | #7929 | `src/bioetl/domain/contracts/gold` | B/major → A/major |
| #7965 | #7824 | `src/bioetl/infrastructure/adapters/pubchem` | B/major → A/major |
| #7966 | #7823 | `src/bioetl/infrastructure/adapters/decorators` | B/major → A/major |
| #7967 | #7809 | `src/bioetl/infrastructure/adapters/http` | B/critical → A/critical |
| #7968 | #7770 | `src/bioetl/application/core/base_transformer` | B/critical → A/critical |
| #7969 | #7760 | `src/bioetl/application/core/postrun` | B/major → A/major |
| #7970 | #7743 | `src/bioetl/composition/bootstrap/cli` | B/major → A/major |
| #7971 | #7744 | `src/bioetl/composition/factories/datasource` | B/major → A/major |
| #7976 | #7825 | `src/bioetl/infrastructure/adapters/chembl` | B/major → A/major |
| #7977 | #7778 | `src/bioetl/application/core/batch_execution` | B/major → A/major |
| #7978 | #7783 | `src/bioetl/application/core/lifecycle` | B/major → A/major |
| #7979 | #7745 | `src/bioetl/composition/bootstrap/assembly` | B/major → A/major |
| #7980 | #7826 | `src/bioetl/infrastructure/adapters/pubmed` | B/major → A/major |
| #7981 | #7904 | `src/bioetl/domain/ports/control_plane` | B/major → A/major |

