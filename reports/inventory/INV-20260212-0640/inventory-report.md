# Code Inventory Report — BioETL
Date: INV-20260212-0640
Scope: src/bioetl/ (all layers)

## Executive Summary
| Метрика | Значение |
|---------|----------|
| Всего классов | 867 |
| Всего функций (module-level) | 561 |
| Всего констант | 171 |
| Мёртвых объектов (DEAD) | 48 |
| Дублей (confirmed) | 1 |
| Дублей (suspected) | 0 |

## 1. Реестр Объектов
### 1.1 Domain Layer
| Type | Name | Module | LOC | Details |
|------|------|--------|-----|---------|
| __all__ | __all__ | bioetl.domain.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.aggregates.__init__ | 1 |  |
| class | Batch | bioetl.domain.aggregates.batch | 431 | public=add_record,add_records,all_records,batch_id,collect_events,create,created_at,mark_committed,mark_failed,mark_writing,metadata,next_index,quarantine_record,quarantined_count,quarantined_records,record_count,records,run_id,seal,sealed_at,status,valid_count |
| class | BatchRecord | bioetl.domain.aggregates.batch | 49 | public=with_validation_error |
| class | BatchStatus | bioetl.domain.aggregates.batch | 21 | bases=StrEnum; public=is_modifiable |
| class | BatchCreated | bioetl.domain.aggregates.events | 9 | bases=DomainEvent |
| class | BatchFailed | bioetl.domain.aggregates.events | 12 | bases=DomainEvent |
| class | BatchSealed | bioetl.domain.aggregates.events | 12 | bases=DomainEvent |
| class | BatchWritten | bioetl.domain.aggregates.events | 10 | bases=DomainEvent |
| class | DomainEvent | bioetl.domain.aggregates.events | 11 |  |
| class | PipelineCompleted | bioetl.domain.aggregates.events | 12 | bases=DomainEvent |
| class | PipelineFailed | bioetl.domain.aggregates.events | 12 | bases=DomainEvent |
| class | PipelineShutdown | bioetl.domain.aggregates.events | 10 | bases=DomainEvent |
| class | QuarantineEntryCreated | bioetl.domain.aggregates.events | 12 | bases=DomainEvent |
| class | QuarantineEntryResolved | bioetl.domain.aggregates.events | 11 | bases=DomainEvent |
| class | RecordQuarantined | bioetl.domain.aggregates.events | 13 | bases=DomainEvent |
| class | PipelineRun | bioetl.domain.aggregates.pipeline_run | 399 | public=collect_events,complete,duration_seconds,ended_at,fail,failed_stages,metadata,pipeline_name,record_stage_failure,record_stage_start,record_stage_success,run_id,run_type,shutdown,stages,start,started_at,status,successful_stages,total_records_processed |
| class | PipelineRunState | bioetl.domain.aggregates.pipeline_run | 20 | bases=StrEnum; public=is_terminal |
| class | StageResult | bioetl.domain.aggregates.pipeline_run | 90 | public=duration_seconds,with_failure,with_success |
| class | StageStatus | bioetl.domain.aggregates.pipeline_run | 8 | bases=StrEnum |
| function | _validate_stage_completion | bioetl.domain.aggregates.pipeline_run | 12 | (status: StageStatus, error: str | None, completed_at: datetime | None) |
| function | _validate_stage_name | bioetl.domain.aggregates.pipeline_run | 4 | (stage: str) |
| function | _validate_stage_result | bioetl.domain.aggregates.pipeline_run | 12 | (stage: str, status: StageStatus, error: str | None, completed_at: datetime | None, records_processed: int) |
| class | QuarantineEntry | bioetl.domain.aggregates.quarantine_entry | 409 | public=add_metadata,age_seconds,batch_id,collect_events,create,created_at,entry_id,error_code,is_resolved,mark_expired,mark_ignored,mark_reprocessed,metadata,payload,payload_hash,pipeline_name,resolution_info,run_id,start_review,status |
| class | QuarantineStatus | bioetl.domain.aggregates.quarantine_entry | 29 | bases=StrEnum; public=can_resolve,is_terminal |
| class | ResolutionInfo | bioetl.domain.aggregates.quarantine_entry | 24 |  |
| function | _validate_quarantine_required_fields | bioetl.domain.aggregates.quarantine_entry | 18 | (entry_id: str, pipeline_name: str, error_code: str, payload: dict[str, Any], payload_hash: ContentHash) |
| __all__ | __all__ | bioetl.domain.composite.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.composite.aggregation | 1 |  |
| class | AggregationConfig | bioetl.domain.composite.aggregation | 29 |  |
| class | AggregationFieldSpec | bioetl.domain.composite.aggregation | 37 | public=effective_output_field |
| class | AggregationFunction | bioetl.domain.composite.aggregation | 40 | bases=Enum; public=from_string |
| class | EnricherCardinality | bioetl.domain.composite.aggregation | 34 | bases=Enum; public=from_string |
| function | _require_non_empty | bioetl.domain.composite.aggregation | 4 | (value: str | tuple[object, ...], name: str) |
| __all__ | __all__ | bioetl.domain.composite.config | 1 |  |
| class | ColumnGroupConfig | bioetl.domain.composite.config | 50 |  |
| class | CompositeConfig | bioetl.domain.composite.config | 212 | public=all_dependency_names,all_enricher_names,get_dependency,get_enricher,lock_key,optional_dependencies,optional_enrichers,required_dependencies,required_enrichers,to_dict |
| class | CompositeDQConfig | bioetl.domain.composite.config | 53 | public=get_enricher_hard_threshold,get_enricher_soft_threshold |
| class | DQOverrideConfig | bioetl.domain.composite.config | 19 |  |
| class | DataSchemaConfig | bioetl.domain.composite.config | 76 | public=get_layer_groups,should_include_group |
| class | DependencyConfig | bioetl.domain.composite.config | 119 | public=effective_filter_fields,is_multi_field_filter,primary_join_key,uses_seed_keys |
| class | EnricherConfig | bioetl.domain.composite.config | 94 | public=has_fallback_keys,is_many_to_one,primary_join_key |
| class | ExecutionConfig | bioetl.domain.composite.config | 30 |  |
| class | LayerColumnConfig | bioetl.domain.composite.config | 73 |  |
| class | LineageConfig | bioetl.domain.composite.config | 12 |  |
| class | MergeConfig | bioetl.domain.composite.config | 114 | public=get_field_priority |
| class | SeedConfig | bioetl.domain.composite.config | 37 |  |
| function | _coerce_column_groups | bioetl.domain.composite.config | 9 | (obj: object, attr: str) |
| function | _coerce_to_tuple | bioetl.domain.composite.config | 5 | (obj: object, attr: str) |
| function | _require_non_empty | bioetl.domain.composite.config | 4 | (value: object, field_name: str) |
| function | _validate_optional_threshold | bioetl.domain.composite.config | 4 | (value: float | None, name: str) |
| function | _validate_positive | bioetl.domain.composite.config | 4 | (value: int | float, field_name: str) |
| function | _validate_positive_limit | bioetl.domain.composite.config | 4 | (limit: int | None, context: str) |
| function | _validate_threshold_order | bioetl.domain.composite.config | 4 | (soft: float | None, hard: float | None) |
| __all__ | __all__ | bioetl.domain.composite.field_groups | 1 |  |
| class | FieldGroupDefinition | bioetl.domain.composite.field_groups | 49 | public=all_columns,base_field_names,field_count |
| class | FieldGroupRegistry | bioetl.domain.composite.field_groups | 208 | public=column_count,field_count,get_columns_by_group,get_field_mapping,get_gold_columns,get_group,get_group_definition,get_ordered_columns,get_trash_columns,groups,is_gold_field,provider_order,validate_columns |
| class | FieldMapping | bioetl.domain.composite.field_groups | 62 | public=get_column,has_provider,provider_count,providers |
| constant | DEFAULT_PROVIDER_ORDER | bioetl.domain.composite.field_groups | 1 |  |
| function | build_field_group_registry | bioetl.domain.composite.field_groups | 20 | (groups: tuple[FieldGroupDefinition, ...], provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER, default_group: FieldGroupId = FieldGroupId.TRASH) |
| class | EnrichmentStatusRecord | bioetl.domain.composite.lineage | 7 |  |
| class | FieldSource | bioetl.domain.composite.lineage | 7 |  |
| class | LineageMetadata | bioetl.domain.composite.lineage | 66 | public=from_dict,has_enrichment,successful_enrichers,to_dict |
| function | _ensure_utc | bioetl.domain.composite.lineage | 3 | (dt: datetime) |
| function | _parse_datetime | bioetl.domain.composite.lineage | 7 | (raw: object) |
| function | _parse_enrichment_status | bioetl.domain.composite.lineage | 13 | (raw: object) |
| function | _parse_field_sources | bioetl.domain.composite.lineage | 5 | (raw: object) |
| function | _parse_providers | bioetl.domain.composite.lineage | 5 | (raw: object) |
| function | _parse_seed_id | bioetl.domain.composite.lineage | 3 | (raw: object) |
| function | _parse_timestamps | bioetl.domain.composite.lineage | 11 | (raw: object) |
| class | CompositeResult | bioetl.domain.composite.result | 152 | public=failed_dependencies,failed_enrichers,is_success,not_run_enrichers,optional_failed_enrichers,required_dependencies_succeeded,required_enrichers_succeeded,skipped_enrichers,successful_dependencies,successful_enrichers,summary,total_records_enriched |
| class | DependencyResult | bioetl.domain.composite.result | 84 | public=failed,is_success,skipped,success,timeout |
| class | DependencyStatus | bioetl.domain.composite.result | 7 | bases=StrEnum |
| class | EnrichmentResult | bioetl.domain.composite.result | 133 | public=enrichment_rate,failed,is_success,not_found_rate,not_run,skipped,success,timeout |
| class | EnrichmentStatus | bioetl.domain.composite.result | 9 | bases=StrEnum |
| class | MergeResult | bioetl.domain.composite.result | 25 | public=enrichment_rate |
| class | SeedResult | bioetl.domain.composite.result | 16 | public=is_success |
| class | CompositePipelineState | bioetl.domain.composite.state | 112 | bases=StrEnum; public=allowed_transitions,can_transition_to,from_string,is_active,is_resumable,is_success,is_terminal,to_metric_value,validate_transition |
| function | can_transition | bioetl.domain.composite.state | 6 | (current: CompositePipelineState, target: CompositePipelineState) |
| function | get_transition_rules | bioetl.domain.composite.state | 15 | () |
| function | validate_transition | bioetl.domain.composite.state | 6 | (current: CompositePipelineState, target: CompositePipelineState) |
| class | ConflictResolution | bioetl.domain.composite.strategy | 51 | bases=StrEnum; public=from_string |
| class | FallbackStrategy | bioetl.domain.composite.strategy | 43 | bases=StrEnum; public=from_string |
| class | MergeStrategy | bioetl.domain.composite.strategy | 46 | bases=StrEnum; public=from_string |
| __all__ | __all__ | bioetl.domain.config.__init__ | 1 |  |
| function | convert_write_mode | bioetl.domain.config._converters | 16 | (mode: _WM | str, enum_cls: type[_WM]) |
| function | freeze_sequences | bioetl.domain.config._converters | 14 | (instance: object, fields: tuple[str, ...]) |
| function | resolve_loading_strategy | bioetl.domain.config._converters | 18 | (loading_strategy: LoadingStrategy | str | None) |
| class | DQConfig | bioetl.domain.config.dq | 53 | public=validate_thresholds |
| class | DQReportConfig | bioetl.domain.config.dq | 16 |  |
| class | MemoryConfig | bioetl.domain.config.memory | 26 |  |
| class | PipelineConfig | bioetl.domain.config.pipeline | 123 | public=gold_table,gold_write_mode,lock_key,on_schema_mismatch,partition_cols,primary_keys,silver_table,write_mode |
| class | RuntimeConfig | bioetl.domain.config.runtime | 78 | public=effective_lock_ttl |
| class | TableConfig | bioetl.domain.config.table | 35 |  |
| class | ConditionalValidation | bioetl.domain.config.validation | 22 |  |
| class | CrossFieldValidation | bioetl.domain.config.validation | 31 |  |
| class | FieldValidation | bioetl.domain.config.validation | 49 |  |
| class | ValidationConfig | bioetl.domain.config.validation | 73 |  |
| constant | DEFAULT_VALIDATION_CONFIG | bioetl.domain.config.validation | 1 |  |
| __all__ | __all__ | bioetl.domain.configs.__init__ | 1 |  |
| class | BaseClientConfig | bioetl.domain.configs.base | 32 |  |
| class | BaseProviderConfig | bioetl.domain.configs.base | 35 | bases=BaseClientConfig |
| class | RateLimitConfig | bioetl.domain.configs.base | 32 |  |
| constant | META_FIELDS | bioetl.domain.constants | 1 |  |
| class | CachedBronzeContext | bioetl.domain.context | 75 | public=disabled,from_options |
| class | InputFilterContext | bioetl.domain.context | 138 | public=disabled,from_csv,from_ids,from_multi_ids |
| class | PipelineContext | bioetl.domain.context | 51 | public=bind_logger,create |
| class | PipelineRunContext | bioetl.domain.context | 61 | public=has_cached_bronze,has_input_filter,vacuum_enabled |
| class | VacuumConfig | bioetl.domain.context | 20 |  |
| function | _now_utc | bioetl.domain.context | 3 | () |
| __all__ | __all__ | bioetl.domain.contracts.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.contracts.gold.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.contracts.gold._base | 1 |  |
| constant | DATE_REGEX | bioetl.domain.contracts.gold._base | 1 |  |
| __all__ | __all__ | bioetl.domain.contracts.gold.chembl | 1 |  |
| class | ChEMBLActivityGoldSchema | bioetl.domain.contracts.gold.chembl | 99 | bases=pa.DataFrameModel |
| class | ChEMBLAssayGoldSchema | bioetl.domain.contracts.gold.chembl | 58 | bases=pa.DataFrameModel |
| class | ChEMBLAssayParametersGoldSchema | bioetl.domain.contracts.gold.chembl | 46 | bases=pa.DataFrameModel |
| class | ChEMBLCellLineGoldSchema | bioetl.domain.contracts.gold.chembl | 37 | bases=pa.DataFrameModel |
| class | ChEMBLCompoundRecordGoldSchema | bioetl.domain.contracts.gold.chembl | 33 | bases=pa.DataFrameModel |
| class | ChEMBLDocumentGoldSchema | bioetl.domain.contracts.gold.chembl | 56 | bases=pa.DataFrameModel |
| class | ChEMBLDocumentSimilarityGoldSchema | bioetl.domain.contracts.gold.chembl | 40 | bases=pa.DataFrameModel |
| class | ChEMBLDocumentTermGoldSchema | bioetl.domain.contracts.gold.chembl | 31 | bases=pa.DataFrameModel |
| class | ChEMBLMoleculeGoldSchema | bioetl.domain.contracts.gold.chembl | 73 | bases=pa.DataFrameModel |
| class | ChEMBLProteinClassGoldSchema | bioetl.domain.contracts.gold.chembl | 40 | bases=pa.DataFrameModel |
| class | ChEMBLSubcellularFractionGoldSchema | bioetl.domain.contracts.gold.chembl | 48 | bases=pa.DataFrameModel |
| class | ChEMBLTargetComponentGoldSchema | bioetl.domain.contracts.gold.chembl | 32 | bases=pa.DataFrameModel |
| class | ChEMBLTargetGoldSchema | bioetl.domain.contracts.gold.chembl | 37 | bases=pa.DataFrameModel |
| class | ChEMBLTissueGoldSchema | bioetl.domain.contracts.gold.chembl | 56 | bases=pa.DataFrameModel |
| __all__ | __all__ | bioetl.domain.contracts.gold.composite | 1 |  |
| class | CompositeMoleculeGoldSchema | bioetl.domain.contracts.gold.composite | 93 | bases=pa.DataFrameModel |
| class | CompositePublicationGoldSchema | bioetl.domain.contracts.gold.composite | 95 | bases=pa.DataFrameModel |
| __all__ | __all__ | bioetl.domain.contracts.gold.pubchem | 1 |  |
| class | PubChemCompoundGoldSchema | bioetl.domain.contracts.gold.pubchem | 31 | bases=pa.DataFrameModel |
| __all__ | __all__ | bioetl.domain.contracts.gold.publications | 1 |  |
| class | CrossRefPublicationGoldSchema | bioetl.domain.contracts.gold.publications | 101 | bases=pa.DataFrameModel |
| class | OpenAlexPublicationGoldSchema | bioetl.domain.contracts.gold.publications | 107 | bases=pa.DataFrameModel |
| class | PubMedPublicationGoldSchema | bioetl.domain.contracts.gold.publications | 125 | bases=pa.DataFrameModel |
| class | SemanticScholarPublicationGoldSchema | bioetl.domain.contracts.gold.publications | 94 | bases=pa.DataFrameModel |
| __all__ | __all__ | bioetl.domain.contracts.gold.uniprot | 1 |  |
| class | UniProtIDMappingGoldSchema | bioetl.domain.contracts.gold.uniprot | 49 | bases=pa.DataFrameModel |
| class | UniProtProteinGoldSchema | bioetl.domain.contracts.gold.uniprot | 68 | bases=pa.DataFrameModel |
| __all__ | __all__ | bioetl.domain.entities.__init__ | 1 |  |
| class | BaseEntity | bioetl.domain.entities.base | 49 |  |
| class | Bioactivity | bioetl.domain.entities.bioactivity | 228 | bases=BaseEntity; public=from_raw,state,with_state |
| class | BioactivityState | bioetl.domain.entities.bioactivity | 14 | bases=StrEnum; public=is_fully_validated,is_ready_for_silver |
| function | _require_field | bioetl.domain.entities.bioactivity | 6 | (raw_data: dict[str, Any], field: str) |
| function | _safe_float | bioetl.domain.entities.bioactivity | 8 | (val: Any) |
| function | _safe_int | bioetl.domain.entities.bioactivity | 8 | (val: Any) |
| function | _safe_json | bioetl.domain.entities.bioactivity | 5 | (val: Any) |
| function | _safe_str | bioetl.domain.entities.bioactivity | 3 | (val: Any) |
| __all__ | __all__ | bioetl.domain.entities.chembl | 1 |  |
| class | ActivityRecord | bioetl.domain.entities.chembl | 169 | bases=BaseModel |
| class | AssayRecord | bioetl.domain.entities.chembl | 105 | bases=BaseModel |
| class | CellLineRecord | bioetl.domain.entities.chembl | 33 | bases=BaseModel |
| class | ChemblPublicationRecord | bioetl.domain.entities.chembl | 49 | bases=BaseModel |
| class | ChemblPublicationTermRecord | bioetl.domain.entities.chembl | 28 | bases=BaseModel |
| class | MoleculeRecord | bioetl.domain.entities.chembl | 148 | bases=BaseModel |
| class | ProteinClassRecord | bioetl.domain.entities.chembl | 32 | bases=BaseModel |
| class | TargetComponentRecord | bioetl.domain.entities.chembl | 34 | bases=BaseModel |
| class | TargetRecord | bioetl.domain.entities.chembl | 65 | bases=BaseModel |
| __all__ | __all__ | bioetl.domain.entities.chembl_activity | 1 |  |
| class | Assay | bioetl.domain.entities.chembl_activity | 76 | bases=BaseEntity |
| __all__ | __all__ | bioetl.domain.entities.chembl_assay_parameters | 1 |  |
| class | AssayParameters | bioetl.domain.entities.chembl_assay_parameters | 83 | bases=BaseEntity; public=get_comparable_value,has_numeric_value,has_text_value |
| class | CompoundRecord | bioetl.domain.entities.chembl_compound_record | 49 | bases=BaseEntity |
| __all__ | __all__ | bioetl.domain.entities.chembl_structures | 1 |  |
| class | CellLine | bioetl.domain.entities.chembl_structures | 50 | bases=BaseEntity |
| class | ChemblPublication | bioetl.domain.entities.chembl_structures | 32 | bases=PublicationEntityBase |
| class | DocumentSimilarity | bioetl.domain.entities.chembl_structures | 45 | bases=BaseEntity |
| class | DocumentTerm | bioetl.domain.entities.chembl_structures | 38 | bases=BaseEntity |
| class | Molecule | bioetl.domain.entities.chembl_structures | 91 | bases=BaseEntity |
| class | ProteinClassification | bioetl.domain.entities.chembl_structures | 59 | bases=BaseEntity; public=is_deprecated,is_root |
| class | Target | bioetl.domain.entities.chembl_structures | 43 | bases=BaseEntity |
| class | TargetComponent | bioetl.domain.entities.chembl_structures | 36 | bases=BaseEntity |
| function | _validate_tanimoto | bioetl.domain.entities.chembl_structures | 4 | (value: float | None, field_name: str) |
| __all__ | __all__ | bioetl.domain.entities.chembl_subcellular_fraction | 1 |  |
| class | SubcellularFraction | bioetl.domain.entities.chembl_subcellular_fraction | 44 | bases=BaseEntity |
| class | Tissue | bioetl.domain.entities.chembl_tissue | 31 | bases=BaseEntity |
| __all__ | __all__ | bioetl.domain.entities.crossref | 1 |  |
| class | CrossRefPublicationEntity | bioetl.domain.entities.crossref | 99 | bases=PublicationEntityBase |
| class | PublicationRecord | bioetl.domain.entities.crossref | 80 | bases=BaseModel |
| __all__ | __all__ | bioetl.domain.entities.openalex | 1 |  |
| class | OpenAlexPublicationEntity | bioetl.domain.entities.openalex | 62 | bases=PublicationEntityBase |
| __all__ | __all__ | bioetl.domain.entities.pubchem | 1 |  |
| class | PubchemMolecule | bioetl.domain.entities.pubchem | 83 | bases=BaseEntity |
| class | PubchemMoleculeRecord | bioetl.domain.entities.pubchem | 155 | bases=BaseModel |
| __all__ | __all__ | bioetl.domain.entities.publication_base | 1 |  |
| class | PublicationEntityBase | bioetl.domain.entities.publication_base | 102 | bases=BaseEntity |
| __all__ | __all__ | bioetl.domain.entities.pubmed | 1 |  |
| class | ArticleRecord | bioetl.domain.entities.pubmed | 99 | bases=BaseModel |
| class | PubMedPublicationEntity | bioetl.domain.entities.pubmed | 115 | bases=PublicationEntityBase |
| __all__ | __all__ | bioetl.domain.entities.semanticscholar | 1 |  |
| class | SemanticScholarPublicationEntity | bioetl.domain.entities.semanticscholar | 89 | bases=PublicationEntityBase |
| __all__ | __all__ | bioetl.domain.entities.uniprot | 1 |  |
| class | IDMappingResult | bioetl.domain.entities.uniprot | 87 | bases=BaseEntity |
| class | UniprotTarget | bioetl.domain.entities.uniprot | 167 | bases=BaseEntity |
| class | ErrorClassifier | bioetl.domain.error_classifier | 98 | public=classify,fallback_usage_count,reset_fallback_count |
| function | _match_error_type | bioetl.domain.error_classifier | 13 | (error_name: str) |
| class | PipelineEvent | bioetl.domain.events | 63 | public=phase_completed,phase_started |
| __all__ | __all__ | bioetl.domain.exceptions.__init__ | 1 |  |
| class | BioETLError | bioetl.domain.exceptions.base | 87 | bases=Exception; public=context,get_error_type,with_context |
| class | CriticalError | bioetl.domain.exceptions.base | 23 | bases=BioETLError; public=get_error_type |
| class | DataQualityError | bioetl.domain.exceptions.base | 23 | bases=BioETLError; public=get_error_type |
| class | RecoverableError | bioetl.domain.exceptions.base | 22 | bases=BioETLError; public=get_error_type |
| class | DataQualityThresholdError | bioetl.domain.exceptions.data_quality | 32 | bases=BioETLError |
| class | BronzeValidationError | bioetl.domain.exceptions.infrastructure | 42 | bases=StorageError |
| class | BucketNotFoundError | bioetl.domain.exceptions.infrastructure | 20 | bases=StorageError |
| class | CachedBronzeEmptyError | bioetl.domain.exceptions.infrastructure | 51 | bases=StorageError |
| class | DeltaOptimizeError | bioetl.domain.exceptions.infrastructure | 38 | bases=StorageError |
| class | DeltaSchemaValidationError | bioetl.domain.exceptions.infrastructure | 53 | bases=CriticalError |
| class | DeltaTransactionError | bioetl.domain.exceptions.infrastructure | 41 | bases=CriticalError |
| class | DeltaWriteConflictError | bioetl.domain.exceptions.infrastructure | 43 | bases=StorageError |
| class | InfrastructureError | bioetl.domain.exceptions.infrastructure | 32 | bases=CriticalError |
| class | SchemaEvolutionError | bioetl.domain.exceptions.infrastructure | 40 | bases=StorageError |
| class | StorageError | bioetl.domain.exceptions.infrastructure | 11 | bases=RecoverableError |
| class | StorageQuotaExceededError | bioetl.domain.exceptions.infrastructure | 42 | bases=CriticalError |
| class | TableNotFoundError | bioetl.domain.exceptions.infrastructure | 20 | bases=StorageError |
| class | UploadError | bioetl.domain.exceptions.infrastructure | 23 | bases=StorageError |
| function | _build_schema_error_message | bioetl.domain.exceptions.infrastructure | 10 | (table: str, new_fields: set[str], removed_fields: set[str]) |
| function | _build_schema_validation_message | bioetl.domain.exceptions.infrastructure | 16 | (table_path: str, expected_columns: list[str], actual_columns: list[str], type_mismatches: dict[str, tuple[str, str]]) |
| function | _format_column_diff | bioetl.domain.exceptions.infrastructure | 12 | (expected_columns: list[str], actual_columns: list[str]) |
| function | _format_type_mismatches | bioetl.domain.exceptions.infrastructure | 9 | (type_mismatches: dict[str, tuple[str, str]]) |
| class | AuthFailureError | bioetl.domain.exceptions.internal | 33 | bases=CriticalError |
| class | CheckpointConflictError | bioetl.domain.exceptions.internal | 27 | bases=CriticalError |
| class | InvalidStateError | bioetl.domain.exceptions.internal | 41 | bases=CriticalError |
| class | LockAcquisitionError | bioetl.domain.exceptions.internal | 28 | bases=CriticalError |
| class | LockLostError | bioetl.domain.exceptions.internal | 29 | bases=CriticalError |
| class | MergeConflictError | bioetl.domain.exceptions.internal | 26 | bases=CriticalError |
| class | MetricsServerError | bioetl.domain.exceptions.internal | 38 | bases=CriticalError |
| class | PolicyViolationError | bioetl.domain.exceptions.internal | 25 | bases=CriticalError |
| class | RunnerAlreadyExecutedError | bioetl.domain.exceptions.internal | 45 | bases=CriticalError |
| class | ApiError | bioetl.domain.exceptions.network | 29 | bases=RecoverableError |
| class | CircuitBreakerOpenError | bioetl.domain.exceptions.network | 28 | bases=RecoverableError |
| class | DataValidationError | bioetl.domain.exceptions.network | 44 | bases=ExternalServiceError |
| class | ExternalServiceError | bioetl.domain.exceptions.network | 42 | bases=RecoverableError |
| class | NetworkError | bioetl.domain.exceptions.network | 24 | bases=RecoverableError |
| class | RateLimitError | bioetl.domain.exceptions.network | 27 | bases=RecoverableError |
| class | RateLimitExceededError | bioetl.domain.exceptions.network | 39 | bases=ExternalServiceError |
| class | RetryExhaustedError | bioetl.domain.exceptions.network | 39 | bases=RecoverableError |
| class | ServiceAuthenticationError | bioetl.domain.exceptions.network | 38 | bases=ExternalServiceError |
| class | ServiceUnavailableError | bioetl.domain.exceptions.network | 42 | bases=ExternalServiceError |
| class | TimeoutError | bioetl.domain.exceptions.network | 26 | bases=RecoverableError |
| class | InvalidDataFormatError | bioetl.domain.exceptions.validation | 31 | bases=ValidationError |
| class | MissingRequiredFieldError | bioetl.domain.exceptions.validation | 26 | bases=ValidationError |
| class | SchemaViolationError | bioetl.domain.exceptions.validation | 25 | bases=ValidationError |
| class | ValidationError | bioetl.domain.exceptions.validation | 15 | bases=DataQualityError |
| __all__ | __all__ | bioetl.domain.filtering.__init__ | 1 |  |
| class | FilterOperator | bioetl.domain.filtering.column_filter | 18 | bases=StrEnum |
| class | GoldColumnFilter | bioetl.domain.filtering.column_filter | 31 |  |
| class | GoldFilterConfig | bioetl.domain.filtering.gold_config | 229 | public=is_empty,should_include |
| class | FilterColumn | bioetl.domain.filtering.input_config | 10 |  |
| class | InputFilterConfig | bioetl.domain.filtering.input_config | 114 | public=get_columns,is_direct_filter,is_direct_multi_filter,is_multi_column |
| class | GoldListContainsFilter | bioetl.domain.filtering.list_filters | 20 |  |
| class | GoldListLengthFilter | bioetl.domain.filtering.list_filters | 21 |  |
| class | FilterLoadResult | bioetl.domain.filtering.load_result | 55 | public=has_duplicates,is_multi_column |
| class | GoldRangeFilter | bioetl.domain.filtering.range_filter | 25 |  |
| class | SilverFilterConfig | bioetl.domain.filtering.silver_config | 34 | bases=GoldFilterConfig; public=from_gold_filter_config |
| class | LockContext | bioetl.domain.locking | 81 | public=create,is_valid,matches_table |
| class | LockContextHolder | bioetl.domain.locking | 50 | public=clear,get,set |
| class | LockNotHeldError | bioetl.domain.locking | 20 | bases=Exception |
| __all__ | __all__ | bioetl.domain.mapping.__init__ | 1 |  |
| constant | PUBLICATION_FIELD_MAPPING | bioetl.domain.mapping.publication_fields | 1 |  |
| constant | UNIFIED_TO_PROVIDER | bioetl.domain.mapping.publication_fields | 1 |  |
| function | _build_reverse_mapping | bioetl.domain.mapping.publication_fields | 6 | () |
| function | apply_field_mapping | bioetl.domain.mapping.publication_fields | 30 | (record: dict[str, Any], provider: ProviderName) |
| function | get_provider_name | bioetl.domain.mapping.publication_fields | 18 | (provider: ProviderName, unified_field: str) |
| function | get_unified_name | bioetl.domain.mapping.publication_fields | 18 | (provider: ProviderName, field_name: str) |
| __all__ | __all__ | bioetl.domain.mapping.publication_type_classification | 1 |  |
| class | PublicationTypeEntry | bioetl.domain.mapping.publication_type_classification | 15 |  |
| constant | CLASSIFICATION_TABLE_SIZE | bioetl.domain.mapping.publication_type_classification | 1 |  |
| function | _best_match | bioetl.domain.mapping.publication_type_classification | 11 | (lookup: dict[str, PublicationTypeEntry], raw_types: list[str]) |
| function | _build_lookups | bioetl.domain.mapping.publication_type_classification | 45 | () |
| function | _get_lookup | bioetl.domain.mapping.publication_type_classification | 3 | (provider: str) |
| function | classify_publication_type | bioetl.domain.mapping.publication_type_classification | 37 | (provider: str, raw_type: str | None = None, raw_types_list: list[str] | None = None) |
| class | ClearPolicy | bioetl.domain.medallion | 19 | bases=StrEnum |
| class | GoldWriteMode | bioetl.domain.medallion | 36 | bases=StrEnum; public=from_string |
| class | Layer | bioetl.domain.medallion | 12 | bases=StrEnum |
| class | LoadingStrategy | bioetl.domain.medallion | 52 | bases=StrEnum; public=allows_checkpoint_resume,from_string |
| class | MedallionPolicy | bioetl.domain.medallion | 67 | public=for_run_type,should_clear_gold,should_clear_silver |
| class | SilverWriteMode | bioetl.domain.medallion | 36 | bases=StrEnum; public=from_string |
| class | WriteMode | bioetl.domain.medallion | 12 | bases=StrEnum |
| class | WriteModePolicy | bioetl.domain.medallion | 43 | public=validate |
| __all__ | __all__ | bioetl.domain.models.__init__ | 1 |  |
| class | ExtractionParams | bioetl.domain.models.filter | 45 | public=empty,is_empty,to_query_dict,to_query_string |
| class | APIRequestDetails | bioetl.domain.models.metadata | 39 | bases=BaseModel |
| class | BaseOutputMetadata | bioetl.domain.models.metadata | 54 | bases=BaseModel; public=write_duration_ms |
| class | BronzeMetadata | bioetl.domain.models.metadata | 26 | bases=BaseModel |
| class | BronzeOutputExt | bioetl.domain.models.metadata | 23 | bases=BaseModel |
| class | ColumnMetrics | bioetl.domain.models.metadata | 16 | bases=BaseModel |
| class | DQSummary | bioetl.domain.models.metadata | 35 | bases=BaseModel; public=null_rates |
| class | DeltaMetrics | bioetl.domain.models.metadata | 32 | bases=BaseModel |
| class | EnvironmentMetadata | bioetl.domain.models.metadata | 12 | bases=BaseModel |
| class | FileOutputMetadata | bioetl.domain.models.metadata | 14 | bases=BaseModel |
| class | GoldMetadata | bioetl.domain.models.metadata | 36 | bases=BaseModel |
| class | GoldOutputExt | bioetl.domain.models.metadata | 19 | bases=BaseModel |
| class | GovernanceLineageConfig | bioetl.domain.models.metadata | 37 | bases=BaseModel |
| class | GovernanceMetadata | bioetl.domain.models.metadata | 40 | bases=BaseModel |
| class | LineageMetadata | bioetl.domain.models.metadata | 24 | bases=BaseModel |
| class | PipelineMetadata | bioetl.domain.models.metadata | 20 | bases=BaseModel |
| class | QualityExpectations | bioetl.domain.models.metadata | 16 | bases=BaseModel |
| class | RateLimitInfo | bioetl.domain.models.metadata | 22 | bases=BaseModel |
| class | RunTypeEnum | bioetl.domain.models.metadata | 6 | bases=StrEnum |
| class | RuntimeMetadata | bioetl.domain.models.metadata | 20 | bases=BaseModel |
| class | SCDMetadata | bioetl.domain.models.metadata | 22 | bases=BaseModel |
| class | SchemaColumnMetadata | bioetl.domain.models.metadata | 12 | bases=BaseModel |
| class | SchemaDrift | bioetl.domain.models.metadata | 16 | bases=BaseModel |
| class | SchemaMetadata | bioetl.domain.models.metadata | 20 | bases=BaseModel |
| class | SilverMetadata | bioetl.domain.models.metadata | 34 | bases=BaseModel |
| class | SilverOutputExt | bioetl.domain.models.metadata | 18 | bases=BaseModel |
| class | SourceMetadata | bioetl.domain.models.metadata | 39 | bases=BaseModel |
| function | _compute_expanded_page | bioetl.domain.normalization | 7 | (first_digits: str, last_digits: str) |
| function | _expand_abbreviated_page | bioetl.domain.normalization | 10 | (first_page: str, last_page_raw: str) |
| function | _extract_date_parts | bioetl.domain.normalization | 6 | (date_parts: list[list[int]] | None) |
| function | _extract_digits | bioetl.domain.normalization | 3 | (s: str) |
| function | _extract_non_digits | bioetl.domain.normalization | 3 | (s: str) |
| function | _filter_valid_strings | bioetl.domain.normalization | 3 | (items: list[Any]) |
| function | _format_parts_to_date | bioetl.domain.normalization | 10 | (parts: list[int]) |
| function | _get_last_day_of_month | bioetl.domain.normalization | 5 | (year: int, month: int) |
| function | _is_abbreviated | bioetl.domain.normalization | 7 | (first_digits: str, last_digits: str) |
| function | _is_electronic_page | bioetl.domain.normalization | 3 | (page: str) |
| function | _is_valid_string | bioetl.domain.normalization | 3 | (item: Any) |
| function | _normalize_and_split_pages | bioetl.domain.normalization | 11 | (page: str) |
| function | _parse_authors_from_delimited | bioetl.domain.normalization | 5 | (text: str) |
| function | _parse_authors_from_json | bioetl.domain.normalization | 6 | (text: str) |
| function | _parse_authors_from_list | bioetl.domain.normalization | 3 | (authors: list[Any]) |
| function | _parse_authors_string | bioetl.domain.normalization | 6 | (text: str) |
| function | _prepare_page_input | bioetl.domain.normalization | 6 | (page: str | None) |
| function | _to_none_if_empty | bioetl.domain.normalization | 3 | (s: str) |
| function | _try_parse_json_array | bioetl.domain.normalization | 7 | (text: str) |
| function | extract_first_item | bioetl.domain.normalization | 5 | (items: list[Any] | None) |
| function | extract_first_string | bioetl.domain.normalization | 5 | (items: list[str] | None) |
| function | format_date_parts | bioetl.domain.normalization | 9 | (date_parts: list[list[int]] | None) |
| function | normalize_doi | bioetl.domain.normalization | 3 | (doi: str | None) |
| function | normalize_pmc_id | bioetl.domain.normalization | 10 | (pmc_id: str | None) |
| function | normalize_string | bioetl.domain.normalization | 6 | (value: str | None) |
| function | normalize_to_string | bioetl.domain.normalization | 6 | (value: Any) |
| function | parse_authors_to_list | bioetl.domain.normalization | 9 | (authors: list[str] | str | None) |
| function | parse_date_field | bioetl.domain.normalization | 10 | (value: str | None, fmt: str = '%Y-%m-%d') |
| function | parse_page_range | bioetl.domain.normalization | 20 | (page: str | None) |
| function | strip_html_tags | bioetl.domain.normalization | 15 | (text: str | None) |
| __all__ | __all__ | bioetl.domain.ports.__init__ | 1 |  |
| class | AuditEntry | bioetl.domain.ports.audit | 39 | public=to_dict |
| class | AuditLayer | bioetl.domain.ports.audit | 11 | bases=StrEnum |
| class | AuditOperation | bioetl.domain.ports.audit | 17 | bases=StrEnum |
| class | AuditPort | bioetl.domain.ports.audit | 54 | bases=Protocol; public=aclose,get_entries,log_write |
| class | CheckpointPort | bioetl.domain.ports.checkpoint | 56 | bases=Protocol; public=aclose,delete,list_all,load,save |
| class | DataNormalizationPort | bioetl.domain.ports.data_normalization | 78 | bases=Protocol; public=format_date_parts,normalize_authors,normalize_doi,normalize_oa_status,normalize_partial_date,normalize_pmid,normalize_string,normalize_to_string,normalize_year,parse_authors_to_list,strip_html_tags |
| class | DataSourcePort | bioetl.domain.ports.data_source | 63 | bases=Protocol; public=aclose,fetch,health_check,provider_name |
| class | FilterableDataSourcePort | bioetl.domain.ports.data_source | 87 | bases=DataSourcePort,Protocol; public=fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered |
| class | DeltaReaderPort | bioetl.domain.ports.delta_reader | 79 | bases=Protocol; public=aclose,get_row_count,get_schema,read_table,table_exists |
| __all__ | __all__ | bioetl.domain.ports.dq_config | 1 |  |
| class | BronzeDQConfigPort | bioetl.domain.ports.dq_config | 32 | bases=Protocol; public=enabled,get_checks_enums,get_format_enum,output_path |
| class | GoldDQConfigPort | bioetl.domain.ports.dq_config | 32 | bases=Protocol; public=enabled,get_checks_enums,get_format_enum,output_path |
| class | SilverDQConfigPort | bioetl.domain.ports.dq_config | 32 | bases=Protocol; public=enabled,get_checks_enums,get_format_enum,output_path |
| __all__ | __all__ | bioetl.domain.ports.dq_report | 1 |  |
| class | BronzeDQAnalyzerPort | bioetl.domain.ports.dq_report | 33 | bases=Protocol; public=analyze |
| class | DQReportWriterPort | bioetl.domain.ports.dq_report | 77 | bases=Protocol; public=write_bronze_report,write_gold_report,write_silver_report |
| class | GoldDQAnalyzerPort | bioetl.domain.ports.dq_report | 43 | bases=Protocol; public=analyze |
| class | SilverDQAnalyzerPort | bioetl.domain.ports.dq_report | 45 | bases=Protocol; public=analyze |
| type_alias | DataContainerDict | bioetl.domain.ports.dq_report | 1 |  |
| class | InputFilterPort | bioetl.domain.ports.filtering | 163 | bases=Protocol; public=load_filter_ids,load_filter_with_fallback,load_multi_column_filter |
| class | HealthCheckPort | bioetl.domain.ports.health_check | 40 | bases=Protocol; public=check_health,provider_name |
| class | HealthCheckResult | bioetl.domain.ports.health_check | 77 | public=is_degraded,is_healthy,is_unhealthy,to_dict,to_metric_labels |
| class | HealthMonitorPort | bioetl.domain.ports.health_check | 65 | bases=Protocol; public=get_all_states,record_error,record_success,update_from_health_check_result |
| class | HealthStatePort | bioetl.domain.ports.health_check | 15 | bases=Protocol; public=consecutive_errors,status |
| class | IDMappingPort | bioetl.domain.ports.idmapping | 58 | bases=Protocol; public=health_check,map_ids,provider_name |
| class | LockPort | bioetl.domain.ports.locking | 90 | bases=Protocol; public=aclose,acquire,heartbeat,release,validate_owner |
| __all__ | __all__ | bioetl.domain.ports.memory | 1 |  |
| class | MemoryMonitorPort | bioetl.domain.ports.memory | 77 | bases=Protocol; public=calculate_max_batch_size,estimate_batch_memory_mb,get_memory_stats,get_recommended_batch_size,is_under_pressure |
| class | MemoryStats | bioetl.domain.ports.memory | 22 | public=is_under_pressure |
| class | MetadataWriterPort | bioetl.domain.ports.metadata | 105 | bases=Protocol; public=aclose,write_bronze_metadata,write_gold_metadata,write_silver_metadata |
| class | BronzeMetadataInput | bioetl.domain.ports.metadata_coordinator | 26 |  |
| class | GoldMetadataInput | bioetl.domain.ports.metadata_coordinator | 35 |  |
| class | MetadataCoordinatorPort | bioetl.domain.ports.metadata_coordinator | 39 | bases=Protocol; public=create_bronze_metadata,create_gold_metadata,create_silver_metadata |
| class | SilverMetadataInput | bioetl.domain.ports.metadata_coordinator | 38 |  |
| class | SilverRef | bioetl.domain.ports.metadata_coordinator | 15 |  |
| class | NoOpAudit | bioetl.domain.ports.noop | 51 | public=aclose,get_entries,log_write |
| class | NoOpMemoryMonitor | bioetl.domain.ports.noop | 84 | public=calculate_max_batch_size,estimate_batch_memory_mb,get_memory_stats,get_recommended_batch_size,is_under_pressure |
| class | NoOpMetadataWriter | bioetl.domain.ports.noop | 92 | public=aclose,write_bronze_metadata,write_gold_metadata,write_silver_metadata |
| class | NoOpMetrics | bioetl.domain.ports.noop | 46 | public=close,increment_counter,observe_histogram,reset_warning,set_gauge |
| class | NoOpPiiHasher | bioetl.domain.ports.noop | 56 | public=get_salt_id,hash_list,hash_value |
| class | NoOpTracing | bioetl.domain.ports.noop | 32 | public=close,get_tracer |
| class | _NoOpOtelTracer | bioetl.domain.ports.noop | 15 | public=start_as_current_span |
| class | _NoOpSpan | bioetl.domain.ports.noop | 27 | public=record_exception,set_attribute,set_status |
| class | DQMonitorPort | bioetl.domain.ports.observability | 183 | bases=Protocol; public=add_metric,check_quality,get_baseline_stats,update_baseline_from_metrics |
| class | LoggerPort | bioetl.domain.ports.observability | 37 | bases=Protocol; public=bind,debug,error,exception,info,warning |
| class | MetricsPort | bioetl.domain.ports.observability | 65 | bases=Protocol; public=close,increment_counter,observe_histogram,set_gauge |
| class | TracingPort | bioetl.domain.ports.observability | 18 | bases=Protocol; public=close,get_tracer |
| class | PiiHasherPort | bioetl.domain.ports.pii | 53 | bases=Protocol; public=get_salt_id,hash_list,hash_value |
| class | QuarantinePort | bioetl.domain.ports.quarantine | 131 | bases=Protocol; public=aclose,get_stats,inspect,purge,replay,update_status,write |
| class | CircuitBreakerPort | bioetl.domain.ports.resilience | 58 | bases=Protocol; public=call,get_failure_count,get_state,reset |
| class | RateLimiterPort | bioetl.domain.ports.resilience | 44 | bases=Protocol; public=acquire,available_tokens,try_acquire |
| constant | P | bioetl.domain.ports.resilience | 1 |  |
| constant | T | bioetl.domain.ports.resilience | 1 |  |
| class | MetricsExtractorPort | bioetl.domain.ports.runner | 22 | bases=Protocol; public=extract_metrics |
| class | RunnablePort | bioetl.domain.ports.runner | 14 | bases=Protocol; public=run,shutdown_signal |
| class | RunnerFactoryPort | bioetl.domain.ports.runner | 45 | bases=Protocol; public=contains,create,list_pipelines |
| __all__ | __all__ | bioetl.domain.ports.serialization | 1 |  |
| class | JsonEncoderPort | bioetl.domain.ports.serialization | 67 | bases=Protocol; public=dumps,dumps_canonical,loads |
| __all__ | __all__ | bioetl.domain.ports.shutdown | 1 |  |
| class | ShutdownPort | bioetl.domain.ports.shutdown | 66 | bases=Protocol; public=initiate_shutdown,is_shutting_down,wait_for_completion |
| class | StoragePort | bioetl.domain.ports.storage | 378 | bases=Protocol; public=aclose,archive,cleanup_bronze,clear_csv,clear_delta,clear_gold,clear_silver,health_check,optimize,preview_cleanup,read_silver,vacuum,write_bronze,write_gold,write_gold_merged,write_silver,write_silver_merged |
| class | GoldValidatorPort | bioetl.domain.ports.validation | 21 | bases=Protocol; public=validate |
| class | SilverValidatorPort | bioetl.domain.ports.validation | 21 | bases=Protocol; public=validate |
| __all__ | __all__ | bioetl.domain.registry.__init__ | 1 |  |
| class | PublicationMapping | bioetl.domain.registry.publication | 48 | public=get_dedup_key_fields |
| constant | ALL_PUBLICATION_ENTITY_TYPES | bioetl.domain.registry.publication | 1 |  |
| constant | LEGACY_PUBLICATION_ALIASES | bioetl.domain.registry.publication | 1 |  |
| constant | PUBLICATION_ENTITY_TYPES | bioetl.domain.registry.publication | 1 |  |
| function | get_dedup_key_fields | bioetl.domain.registry.publication | 26 | (entity_type: str) |
| function | get_publication_mapping | bioetl.domain.registry.publication | 17 | (entity_type: str) |
| function | has_composite_key | bioetl.domain.registry.publication | 19 | (entity_type: str) |
| function | is_legacy_publication_alias | bioetl.domain.registry.publication | 19 | (entity_type: str) |
| function | is_publication_entity | bioetl.domain.registry.publication | 20 | (entity_type: str) |
| function | validate_publication_entity_type | bioetl.domain.registry.publication | 45 | (entity_type: str, provider: str) |
| class | AdapterConfig | bioetl.domain.resilience | 36 |  |
| class | CircuitBreakerConfig | bioetl.domain.resilience | 20 |  |
| class | RetryConfig | bioetl.domain.resilience | 103 | public=calculate_delay,is_last_attempt,is_retryable_exception,is_retryable_status |
| constant | DEFAULT_RETRYABLE_STATUSES | bioetl.domain.resilience | 1 |  |
| function | _validate_non_negative | bioetl.domain.resilience | 4 | (name: str, value: int) |
| function | _validate_positive | bioetl.domain.resilience | 4 | (name: str, value: int | float) |
| __all__ | __all__ | bioetl.domain.schemas.__init__ | 1 |  |
| class | ETLRecordSchema | bioetl.domain.schemas.base | 63 | bases=pa.DataFrameModel |
| constant | ISO8601_TIMESTAMP_REGEX | bioetl.domain.schemas.base | 1 |  |
| class | ActivitySchema | bioetl.domain.schemas.chembl.activity | 207 | bases=ETLRecordSchema |
| class | AssaySchema | bioetl.domain.schemas.chembl.assay | 197 | bases=ETLRecordSchema |
| __all__ | __all__ | bioetl.domain.schemas.chembl.assay_parameters | 1 |  |
| class | AssayParametersSchema | bioetl.domain.schemas.chembl.assay_parameters | 91 | bases=ETLRecordSchema |
| class | CellLineSchema | bioetl.domain.schemas.chembl.cell_line | 73 | bases=ETLRecordSchema |
| class | CompoundRecordSchema | bioetl.domain.schemas.chembl.compound_record | 56 | bases=ETLRecordSchema |
| class | MoleculeSchema | bioetl.domain.schemas.chembl.molecule | 235 | bases=ETLRecordSchema |
| class | ProteinClassificationSchema | bioetl.domain.schemas.chembl.protein_classification | 43 | bases=ETLRecordSchema |
| __all__ | __all__ | bioetl.domain.schemas.chembl.publication | 1 |  |
| class | ChemblPublicationSchema | bioetl.domain.schemas.chembl.publication | 71 | bases=PublicationBaseSchema |
| class | PublicationSimilaritySchema | bioetl.domain.schemas.chembl.publication_similarity | 54 | bases=ETLRecordSchema |
| class | PublicationTermSchema | bioetl.domain.schemas.chembl.publication_term | 46 | bases=ETLRecordSchema |
| class | TargetSchema | bioetl.domain.schemas.chembl.target | 88 | bases=ETLRecordSchema |
| class | TargetComponentSchema | bioetl.domain.schemas.chembl.target_component | 35 | bases=ETLRecordSchema |
| __all__ | __all__ | bioetl.domain.schemas.column_order | 1 |  |
| constant | ALL_SYSTEM_FIELDS | bioetl.domain.schemas.column_order | 1 |  |
| constant | DQ_FIELDS_SUFFIX | bioetl.domain.schemas.column_order | 1 |  |
| constant | LOOKUP_FIELDS_PREFIX | bioetl.domain.schemas.column_order | 1 |  |
| constant | PUBLICATION_CROSSREF_FIELDS | bioetl.domain.schemas.column_order | 1 |  |
| constant | PUBLICATION_METADATA_FIELDS | bioetl.domain.schemas.column_order | 1 |  |
| constant | PUBLICATION_UNIFIED_FIELDS | bioetl.domain.schemas.column_order | 1 |  |
| constant | SYSTEM_FIELDS_PREFIX | bioetl.domain.schemas.column_order | 1 |  |
| function | _filter_present | bioetl.domain.schemas.column_order | 5 | (ordered_fields: tuple[str, ...], present: frozenset[str]) |
| function | canonical_column_order | bioetl.domain.schemas.column_order | 39 | (columns: list[str] | tuple[str, ...]) |
| __all__ | __all__ | bioetl.domain.schemas.common.__init__ | 1 |  |
| class | PublicationBaseSchema | bioetl.domain.schemas.common.publication_base | 171 | bases=ETLRecordSchema |
| constant | LOOKUP_METHODS | bioetl.domain.schemas.common.publication_base | 1 |  |
| constant | OA_STATUS_VALUES | bioetl.domain.schemas.common.publication_base | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.constants | 1 |  |
| constant | ACTIVITY_STANDARD_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | ASSAY_CATEGORIES | bioetl.domain.schemas.constants | 1 |  |
| constant | ASSAY_PARAMETER_STANDARD_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | ASSAY_TEST_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | ASSAY_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | BAO_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | CELLOSAURUS_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | CHEMBL_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | CLO_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | DATA_VALIDITY_COMMENTS | bioetl.domain.schemas.constants | 1 |  |
| constant | EFO_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | ISO_DATE_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | ISSN_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | MAX_PHASE_VALUES | bioetl.domain.schemas.constants | 1 |  |
| constant | MOLECULE_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | ORCID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| constant | PUBLICATION_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | RELATIONSHIP_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | STANDARD_RELATIONS | bioetl.domain.schemas.constants | 1 |  |
| constant | STRUCTURE_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | TARGET_COMPONENT_RELATIONSHIPS | bioetl.domain.schemas.constants | 1 |  |
| constant | TARGET_TYPES | bioetl.domain.schemas.constants | 1 |  |
| constant | UO_ID_PATTERN | bioetl.domain.schemas.constants | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.crossref.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.crossref.publication | 1 |  |
| class | PublicationEnrichedSchema | bioetl.domain.schemas.crossref.publication | 146 | bases=PublicationBaseSchema |
| __all__ | __all__ | bioetl.domain.schemas.crossref.work | 1 |  |
| class | PublicationSchema | bioetl.domain.schemas.crossref.work | 109 | bases=ETLRecordSchema |
| constant | PUBLICATION_TYPES | bioetl.domain.schemas.crossref.work | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.openalex.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.openalex.publication | 1 |  |
| class | OpenAlexPublicationSchema | bioetl.domain.schemas.openalex.publication | 153 | bases=PublicationBaseSchema |
| __all__ | __all__ | bioetl.domain.schemas.pubchem.compound | 1 |  |
| class | PubchemMoleculeSchema | bioetl.domain.schemas.pubchem.compound | 389 | bases=ETLRecordSchema |
| __all__ | __all__ | bioetl.domain.schemas.pubmed.publication | 1 |  |
| class | PubMedPublicationSchema | bioetl.domain.schemas.pubmed.publication | 260 | bases=PublicationBaseSchema |
| constant | ISSN_TYPES | bioetl.domain.schemas.pubmed.publication | 1 |  |
| constant | PUBLICATION_STATUSES | bioetl.domain.schemas.pubmed.publication | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.semanticscholar.__init__ | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.semanticscholar.publication | 1 |  |
| class | SemanticScholarPublicationSchema | bioetl.domain.schemas.semanticscholar.publication | 135 | bases=PublicationBaseSchema |
| __all__ | __all__ | bioetl.domain.schemas.uniprot.idmapping | 1 |  |
| class | IDMappingSchema | bioetl.domain.schemas.uniprot.idmapping | 115 | bases=ETLRecordSchema |
| constant | MAPPING_STATUSES | bioetl.domain.schemas.uniprot.idmapping | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.uniprot.protein | 1 |  |
| class | UniprotTargetSchema | bioetl.domain.schemas.uniprot.protein | 432 | bases=ETLRecordSchema |
| constant | ENTRY_TYPES | bioetl.domain.schemas.uniprot.protein | 1 |  |
| constant | PROTEIN_EXISTENCE_LEVELS | bioetl.domain.schemas.uniprot.protein | 1 |  |
| constant | PROTEIN_FLAGS | bioetl.domain.schemas.uniprot.protein | 1 |  |
| __all__ | __all__ | bioetl.domain.schemas.validators | 1 |  |
| function | in_closed_range | bioetl.domain.schemas.validators | 14 | (pandas_obj: pd.Series, *, min_val: int | float, max_val: int | float) |
| function | is_non_negative | bioetl.domain.schemas.validators | 13 | (pandas_obj: pd.Series, *, min_value: float | bool = 0) |
| function | is_positive | bioetl.domain.schemas.validators | 13 | (pandas_obj: pd.Series, *, min_value: int | bool = 1) |
| function | is_valid_json | bioetl.domain.schemas.validators | 20 | (series: pd.Series) |
| function | is_valid_json_array | bioetl.domain.schemas.validators | 20 | (series: pd.Series) |
| function | is_valid_json_object | bioetl.domain.schemas.validators | 20 | (series: pd.Series) |
| function | max_str_length | bioetl.domain.schemas.validators | 7 | (pandas_obj: pd.Series, *, max_len: int) |
| function | str_matches_pattern | bioetl.domain.schemas.validators | 7 | (pandas_obj: pd.Series, *, pattern: str) |
| function | str_starts_with | bioetl.domain.schemas.validators | 7 | (pandas_obj: pd.Series, *, prefix: str) |
| __all__ | __all__ | bioetl.domain.serialization | 1 |  |
| function | _deserialize_with_orjson | bioetl.domain.serialization | 8 | (data: str | bytes) |
| function | _deserialize_with_stdlib | bioetl.domain.serialization | 9 | (data: str | bytes) |
| function | _escape_non_ascii | bioetl.domain.serialization | 3 | (text: str) |
| function | _get_orjson_options | bioetl.domain.serialization | 6 | (sort_keys: bool) |
| function | _has_non_ascii | bioetl.domain.serialization | 3 | (text: str) |
| function | _serialize_with_orjson | bioetl.domain.serialization | 13 | (data: dict[str, Any] | list[Any], *, sort_keys: bool = True, ensure_ascii: bool = True) |
| function | _serialize_with_stdlib | bioetl.domain.serialization | 15 | (data: dict[str, Any] | list[Any], *, sort_keys: bool = True, ensure_ascii: bool = True) |
| function | deserialize_from_json | bioetl.domain.serialization | 25 | (data: str | bytes) |
| function | flatten_arrow_table_for_export | bioetl.domain.serialization | 56 | (table: pa.Table) |
| function | is_orjson_available | bioetl.domain.serialization | 8 | () |
| function | serialize_to_json | bioetl.domain.serialization | 36 | (data: dict[str, Any] | list[Any], *, sort_keys: bool = True, ensure_ascii: bool = True) |
| function | serialize_to_json_canonical | bioetl.domain.serialization | 23 | (data: dict[str, Any]) |
| __all__ | __all__ | bioetl.domain.services.__init__ | 1 |  |
| class | ActivityAggregator | bioetl.domain.services.activity_aggregator | 308 | public=aggregate_concentrations,aggregate_concentrations_with_uncertainty,aggregate_values,aggregate_with_uncertainty,filter_and_aggregate,weighted_aggregate |
| class | AggregationMethod | bioetl.domain.services.activity_aggregator | 8 | bases=StrEnum |
| function | _geometric_mean | bioetl.domain.services.activity_aggregator | 21 | (values: Sequence[float]) |
| function | _median_absolute_deviation | bioetl.domain.services.activity_aggregator | 17 | (values: Sequence[float]) |
| class | DataNormalizationConfig | bioetl.domain.services.data_normalization_config | 55 | public=for_modern_publications,for_scientific_publications |
| class | DefaultDataNormalizationService | bioetl.domain.services.data_normalization_service | 249 | public=format_date_parts,normalize_authors,normalize_doi,normalize_oa_status,normalize_partial_date,normalize_pmid,normalize_string,normalize_to_string,normalize_year,parse_authors_to_list,strip_html_tags |
| __all__ | __all__ | bioetl.domain.services.dq_metrics_calculator | 1 |  |
| class | DQMetricsCalculator | bioetl.domain.services.dq_metrics_calculator | 84 | public=calculate |
| class | DQMetricsInput | bioetl.domain.services.dq_metrics_calculator | 15 |  |
| __all__ | __all__ | bioetl.domain.services.dq_serializer | 1 |  |
| class | DQReportSerializer | bioetl.domain.services.dq_serializer | 367 | public=serialize,to_dict |
| function | _is_dataclass_instance | bioetl.domain.services.dq_serializer | 3 | (value: Any) |
| function | _serialize_collection | bioetl.domain.services.dq_serializer | 5 | (value: dict[str, Any] | list[Any] | tuple[Any, ...]) |
| function | _serialize_dataclass | bioetl.domain.services.dq_serializer | 6 | (value: Any) |
| function | _serialize_value | bioetl.domain.services.dq_serializer | 11 | (value: Any) |
| function | to_dict | bioetl.domain.services.dq_serializer | 16 | (obj: Any) |
| class | IdentityService | bioetl.domain.services.identity_service | 123 | public=compute_content_hash,compute_entity_id |
| class | ConcentrationRangeConfig | bioetl.domain.services.normalization_config | 19 |  |
| class | NormalizationConfig | bioetl.domain.services.normalization_config | 91 | public=for_medicinal_chemistry,for_screening,strict |
| class | PChemblRangeConfig | bioetl.domain.services.normalization_config | 33 |  |
| class | NormalizationResult | bioetl.domain.services.normalization_service | 18 |  |
| class | NormalizationService | bioetl.domain.services.normalization_service | 364 | public=classify_potency,is_highly_potent,is_potent,normalize_activity,normalize_concentrations,normalize_multiple,normalize_to_pchembl |
| class | UnitConverter | bioetl.domain.services.unit_converter | 201 | public=convert,normalize_to_micromolar,normalize_to_nanomolar,pchembl_to_concentration,to_concentration,to_pchembl,value_to_pchembl |
| class | ValueValidator | bioetl.domain.services.value_validator | 309 | public=is_highly_potent,is_potent,set_concentration_range,validate_activity_value,validate_concentration,validate_pchembl |
| constant | DEFAULT_CONCENTRATION_RANGES | bioetl.domain.services.value_validator | 1 |  |
| constant | PCHEMBL_MAX | bioetl.domain.services.value_validator | 1 |  |
| constant | PCHEMBL_MIN | bioetl.domain.services.value_validator | 1 |  |
| constant | PCHEMBL_TYPICAL_MAX | bioetl.domain.services.value_validator | 1 |  |
| constant | PCHEMBL_TYPICAL_MIN | bioetl.domain.services.value_validator | 1 |  |
| function | _normalize_date | bioetl.domain.transformations | 3 | (value: date) |
| function | _normalize_datetime | bioetl.domain.transformations | 3 | (value: datetime) |
| function | _normalize_dict | bioetl.domain.transformations | 3 | (value: dict[str, Any]) |
| function | _normalize_float | bioetl.domain.transformations | 5 | (value: float) |
| function | _normalize_list | bioetl.domain.transformations | 3 | (value: list[Any]) |
| function | _normalize_str | bioetl.domain.transformations | 3 | (value: str) |
| function | _normalize_value | bioetl.domain.transformations | 3 | (value: Any) |
| function | _should_include_field | bioetl.domain.transformations | 5 | (key: str, value: Any, exclude_none: bool) |
| function | calculate_dq_score | bioetl.domain.transformations | 5 | (valid_count: int, total_count: int) |
| function | canonical_json_dumps | bioetl.domain.transformations | 7 | (obj: dict[str, Any]) |
| function | detect_hash_collision | bioetl.domain.transformations | 7 | (_: ContentHash, source_record_id: str, existing_source_id: str | None) |
| function | detect_schema_drift | bioetl.domain.transformations | 23 | (old_schema: set[str], new_schema: set[str], required_fields: set[str] | None = None) |
| function | exceeds_threshold | bioetl.domain.transformations | 11 | (error_count: int, total_count: int, soft_threshold: float = 0.05, hard_threshold: float = 0.2) |
| function | generate_content_hash | bioetl.domain.transformations | 9 | (record: dict[str, Any], provider: str, exclude_none: bool = False) |
| function | generate_entity_id | bioetl.domain.transformations | 11 | (record: dict[str, Any], provider: str, id_field: str | None = None) |
| function | normalize_for_hash | bioetl.domain.transformations | 9 | (record: dict[str, Any], exclude_none: bool = False) |
| function | safe_float | bioetl.domain.transformations | 16 | (value: Any, default: float | None = None) |
| function | safe_int | bioetl.domain.transformations | 16 | (value: Any, default: int | None = None) |
| function | safe_str | bioetl.domain.transformations | 19 | (value: Any, default: str | None = None) |
| class | BronzeRecord | bioetl.domain.types | 2 | bases=TypedDict |
| class | CircuitBreakerState | bioetl.domain.types | 25 | bases=StrEnum; public=to_metric_value |
| class | ComponentHealthResult | bioetl.domain.types | 14 |  |
| class | ConfigValidationError | bioetl.domain.types | 16 |  |
| class | DataClassification | bioetl.domain.types | 11 | bases=StrEnum |
| class | DriftLevel | bioetl.domain.types | 12 | bases=StrEnum |
| class | ErrorType | bioetl.domain.types | 74 | bases=StrEnum; public=is_critical,is_data_quality,is_recoverable |
| class | HealthReport | bioetl.domain.types | 32 | public=get_failures,is_healthy,overall_status |
| class | HealthStatus | bioetl.domain.types | 26 | bases=StrEnum; public=to_metric_value |
| class | PreflightReport | bioetl.domain.types | 27 | public=is_valid,should_block_startup |
| class | QuarantineRecordStatus | bioetl.domain.types | 25 | bases=StrEnum |
| class | RunType | bioetl.domain.types | 23 | bases=StrEnum; public=priority |
| class | SilverRecord | bioetl.domain.types | 5 | bases=TypedDict |
| class | ValidationResult | bioetl.domain.types | 10 |  |
| type_alias | ArrowSchema | bioetl.domain.types | 1 |  |
| constant | DOI_REGEX_PATTERN | bioetl.domain.validation | 1 |  |
| constant | INCHI_KEY_REGEX_PATTERN | bioetl.domain.validation | 1 |  |
| constant | MAX_MOLECULAR_WEIGHT | bioetl.domain.validation | 1 |  |
| constant | MAX_PUBLICATION_YEAR | bioetl.domain.validation | 1 |  |
| constant | MIN_MOLECULAR_WEIGHT | bioetl.domain.validation | 1 |  |
| constant | MIN_PUBLICATION_YEAR | bioetl.domain.validation | 1 |  |
| function | _get_default_config | bioetl.domain.validation | 5 | () |
| function | validate_doi | bioetl.domain.validation | 25 | (doi: str | None) |
| function | validate_inchi_key | bioetl.domain.validation | 28 | (key: str | None) |
| function | validate_molecular_weight | bioetl.domain.validation | 58 | (value: Any, config: ValidationConfig | None = None) |
| function | validate_non_empty_string | bioetl.domain.validation | 22 | (value: str | None) |
| function | validate_non_negative | bioetl.domain.validation | 31 | (value: Any) |
| function | validate_positive_int | bioetl.domain.validation | 28 | (value: Any) |
| function | validate_publication_year | bioetl.domain.validation | 43 | (year: int | None, config: ValidationConfig | None = None) |
| function | validate_smiles | bioetl.domain.validation | 33 | (smiles: str | None) |
| function | validate_year_range | bioetl.domain.validation | 29 | (year: int | None, min_year: int = MIN_PUBLICATION_YEAR, max_year: int = MAX_PUBLICATION_YEAR) |
| __all__ | __all__ | bioetl.domain.value_objects.__init__ | 1 |  |
| class | ISSN | bioetl.domain.value_objects.academic_ids | 50 | bases=ValueObject[str]; public=compact,from_raw |
| class | ORCID | bioetl.domain.value_objects.academic_ids | 71 | bases=ValueObject[str]; public=compact,from_raw,url |
| class | OpenAlexId | bioetl.domain.value_objects.academic_ids | 61 | bases=ValueObject[str]; public=from_raw,numeric_id,url |
| class | SemanticScholarId | bioetl.domain.value_objects.academic_ids | 45 | bases=ValueObject[str]; public=from_raw |
| class | ActivityValue | bioetl.domain.value_objects.activity | 104 | public=from_raw,is_bounded,is_exact,to_concentration |
| class | ConfidenceScore | bioetl.domain.value_objects.activity | 114 | public=description,from_value,is_high_confidence,is_molecular_target |
| class | RelationOperator | bioetl.domain.value_objects.activity | 85 | bases=StrEnum; public=from_string,is_exact,is_lower_bound,is_upper_bound |
| class | ActivityType | bioetl.domain.value_objects.activity_values | 110 | bases=StrEnum; public=from_string,is_binding_type,is_inhibition_type |
| class | Concentration | bioetl.domain.value_objects.activity_values | 95 | public=from_string,molar_value,to_molar,to_nanomolar,to_unit |
| class | ConcentrationUnit | bioetl.domain.value_objects.activity_values | 57 | bases=StrEnum; public=from_string,to_molar_factor |
| class | PChemblValue | bioetl.domain.value_objects.activity_values | 141 | public=from_concentration,from_molar,is_highly_potent,is_potent,to_concentration,to_molar |
| class | ValueObject | bioetl.domain.value_objects.base | 73 | bases=ABC,Generic[T]; public=value |
| constant | T | bioetl.domain.value_objects.base | 1 |  |
| class | BronzeWriteResult | bioetl.domain.value_objects.bronze_result | 76 | public=compression_ratio |
| class | InChIKey | bioetl.domain.value_objects.chemical | 104 | bases=ValueObject[str]; public=connectivity_layer,from_raw,protonation_layer,stereochemistry_layer |
| class | MolecularWeight | bioetl.domain.value_objects.chemical | 144 | bases=ValueObject[float]; public=from_raw,max_weight,min_weight |
| class | PublicationYear | bioetl.domain.value_objects.chemical | 202 | bases=ValueObject[int]; public=century,decade,from_raw,max_year,min_year |
| class | SMILES | bioetl.domain.value_objects.chemical | 112 | bases=ValueObject[str]; public=canonical,from_raw,is_canonical |
| __all__ | __all__ | bioetl.domain.value_objects.column_order | 1 |  |
| class | ColumnOrderConfig | bioetl.domain.value_objects.column_order | 70 | public=get_group,get_provider_rank |
| class | SemanticGroup | bioetl.domain.value_objects.column_order | 17 | bases=IntEnum |
| constant | DEFAULT_COLUMN_ORDER | bioetl.domain.value_objects.column_order | 1 |  |
| constant | PUBLICATION_FIELD_GROUPS | bioetl.domain.value_objects.column_order | 1 |  |
| __all__ | __all__ | bioetl.domain.value_objects.column_qualifier | 1 |  |
| class | ColumnQualifier | bioetl.domain.value_objects.column_qualifier | 139 | public=extract_field,from_pipeline,is_join_key,is_qualified,parse,prefix |
| constant | JOIN_KEY_COLUMNS | bioetl.domain.value_objects.column_qualifier | 1 |  |
| class | AssayId | bioetl.domain.value_objects.compound_ids | 76 | bases=ValueObject[str]; public=as_chembl_id,from_string,numeric_id |
| class | CompoundId | bioetl.domain.value_objects.compound_ids | 160 | public=as_chembl_id,as_pubchem_cid,from_chembl,from_pubchem,from_raw,is_chembl,is_pubchem,numeric_id |
| class | CompoundSource | bioetl.domain.value_objects.compound_ids | 8 | bases=StrEnum |
| __all__ | __all__ | bioetl.domain.value_objects.dq_metrics | 1 |  |
| class | BatchDQMetrics | bioetl.domain.value_objects.dq_metrics | 132 | public=error_rate,from_records,to_dq_summary,validation_passed |
| class | ColumnStats | bioetl.domain.value_objects.dq_metrics | 32 | public=to_column_metrics |
| class | SchemaDriftInfo | bioetl.domain.value_objects.dq_metrics | 38 | public=has_drift,to_schema_drift |
| function | _calculate_null_rate | bioetl.domain.value_objects.dq_metrics | 12 | (values: list[Any], total: int) |
| function | _calculate_unique_count | bioetl.domain.value_objects.dq_metrics | 16 | (values: list[Any]) |
| function | _collect_all_columns | bioetl.domain.value_objects.dq_metrics | 13 | (records: list[dict[str, Any]]) |
| function | _compute_column_stats | bioetl.domain.value_objects.dq_metrics | 19 | (records: list[dict[str, Any]]) |
| function | _compute_numeric_stats | bioetl.domain.value_objects.dq_metrics | 20 | (values: list[Any]) |
| function | _compute_single_column_stats | bioetl.domain.value_objects.dq_metrics | 26 | (records: list[dict[str, Any]], col_name: str) |
| function | _extract_numeric_values | bioetl.domain.value_objects.dq_metrics | 10 | (values: list[Any]) |
| function | _filter_non_null | bioetl.domain.value_objects.dq_metrics | 10 | (values: list[Any]) |
| function | _is_valid_numeric | bioetl.domain.value_objects.dq_metrics | 16 | (v: Any) |
| function | _make_hashable | bioetl.domain.value_objects.dq_metrics | 16 | (value: Any) |
| __all__ | __all__ | bioetl.domain.value_objects.dq_report | 1 |  |
| class | AnomalyDetectionResult | bioetl.domain.value_objects.dq_report | 18 |  |
| class | AnomalyMetric | bioetl.domain.value_objects.dq_report | 10 |  |
| class | BronzeDQCheckType | bioetl.domain.value_objects.dq_report | 8 | bases=StrEnum |
| class | BronzeDQReport | bioetl.domain.value_objects.dq_report | 27 |  |
| class | BusinessRuleResult | bioetl.domain.value_objects.dq_report | 8 |  |
| class | BusinessRulesResult | bioetl.domain.value_objects.dq_report | 13 |  |
| class | CategoricalDistribution | bioetl.domain.value_objects.dq_report | 10 |  |
| class | CompletenessResult | bioetl.domain.value_objects.dq_report | 7 |  |
| class | ContentHashIntegrityResult | bioetl.domain.value_objects.dq_report | 7 |  |
| class | DQCheckStatus | bioetl.domain.value_objects.dq_report | 6 | bases=StrEnum |
| class | DQReportFormat | bioetl.domain.value_objects.dq_report | 6 | bases=StrEnum |
| class | DQReportStatus | bioetl.domain.value_objects.dq_report | 6 | bases=StrEnum |
| class | DQReportSummary | bioetl.domain.value_objects.dq_report | 8 |  |
| class | DQThresholds | bioetl.domain.value_objects.dq_report | 7 |  |
| class | DataFreshnessResult | bioetl.domain.value_objects.dq_report | 7 |  |
| class | DeduplicationStatsResult | bioetl.domain.value_objects.dq_report | 8 |  |
| class | EncodingValidationResult | bioetl.domain.value_objects.dq_report | 13 |  |
| class | FileIntegrityResult | bioetl.domain.value_objects.dq_report | 7 |  |
| class | ForeignKeyResult | bioetl.domain.value_objects.dq_report | 9 |  |
| class | GoldDQCheckType | bioetl.domain.value_objects.dq_report | 10 | bases=StrEnum |
| class | GoldDQReport | bioetl.domain.value_objects.dq_report | 27 |  |
| class | NullRateResult | bioetl.domain.value_objects.dq_report | 7 |  |
| class | NumericDistribution | bioetl.domain.value_objects.dq_report | 12 |  |
| class | RecordCountResult | bioetl.domain.value_objects.dq_report | 10 |  |
| class | ReferentialIntegrityResult | bioetl.domain.value_objects.dq_report | 5 |  |
| class | SCDIntegrityResult | bioetl.domain.value_objects.dq_report | 11 |  |
| class | SchemaDriftResult | bioetl.domain.value_objects.dq_report | 17 |  |
| class | SchemaSnapshotResult | bioetl.domain.value_objects.dq_report | 21 |  |
| class | SilverDQCheckType | bioetl.domain.value_objects.dq_report | 11 | bases=StrEnum |
| class | SilverDQReport | bioetl.domain.value_objects.dq_report | 34 |  |
| class | StatisticalMetric | bioetl.domain.value_objects.dq_report | 9 |  |
| class | StatisticalProfileResult | bioetl.domain.value_objects.dq_report | 6 |  |
| class | TypeConformanceResult | bioetl.domain.value_objects.dq_report | 13 |  |
| class | UniquenessResult | bioetl.domain.value_objects.dq_report | 9 |  |
| class | ValueDistributionResult | bioetl.domain.value_objects.dq_report | 8 |  |
| __all__ | __all__ | bioetl.domain.value_objects.dq_result | 1 |  |
| class | DQEvaluationStatus | bioetl.domain.value_objects.dq_result | 24 | bases=StrEnum |
| class | DQResult | bioetl.domain.value_objects.dq_result | 44 | public=anomalies_count,is_failed,is_passed,is_warning |
| class | ChemblId | bioetl.domain.value_objects.identifiers | 74 | bases=ValueObject[str]; public=from_raw,numeric_id |
| class | PubChemCid | bioetl.domain.value_objects.identifiers | 67 | bases=ValueObject[int]; public=from_raw |
| class | UniProtId | bioetl.domain.value_objects.identifiers | 87 | bases=ValueObject[str]; public=from_raw,is_primary_format |
| __all__ | __all__ | bioetl.domain.value_objects.publication_field_groups | 1 |  |
| class | FieldGroupConfig | bioetl.domain.value_objects.publication_field_groups | 195 | public=get_columns_by_group,get_field_providers,get_gold_columns,get_group,get_provider_rank,get_trash_columns,group_columns,is_gold_field,sort_columns |
| class | PublicationFieldGroup | bioetl.domain.value_objects.publication_field_groups | 69 | bases=StrEnum; public=display_name,excluded_groups,from_string,gold_groups,include_in_gold |
| constant | DEFAULT_FIELD_GROUP_CONFIG | bioetl.domain.value_objects.publication_field_groups | 1 |  |
| constant | FIELD_TO_GROUP_MAPPING | bioetl.domain.value_objects.publication_field_groups | 1 |  |
| class | DOI | bioetl.domain.value_objects.publications | 103 | bases=ValueObject[str]; public=from_raw,registrant_code,url |
| class | PubMedId | bioetl.domain.value_objects.publications | 73 | bases=ValueObject[str]; public=as_int,from_raw |
| class | RunContext | bioetl.domain.value_objects.run_context | 111 | public=create |
| class | SilverWriteResult | bioetl.domain.value_objects.silver_result | 50 |  |
| class | TaxonomyId | bioetl.domain.value_objects.taxonomy_id | 115 | bases=ValueObject[int]; public=as_str,from_raw,ncbi_url |
| function | validate_taxonomy_id | bioetl.domain.value_objects.taxonomy_id | 24 | (value: str | int | None) |
| function | validate_taxonomy_id_str | bioetl.domain.value_objects.taxonomy_id | 24 | (value: str | int | None) |

### 1.2 Application Layer
| Type | Name | Module | LOC | Details |
|------|------|--------|-----|---------|
| __all__ | __all__ | bioetl.application.composite.__init__ | 1 |  |
| __all__ | __all__ | bioetl.application.composite.aggregator | 1 |  |
| class | EnricherAggregator | bioetl.application.composite.aggregator | 115 | public=aggregate |
| class | CompositeCheckpointManager | bioetl.application.composite.checkpoint | 208 | public=delete,list_all,load,save |
| class | CompositeCheckpointState | bioetl.application.composite.checkpoint | 304 | public=from_dict,is_resumable,to_dict,with_dependency_completed,with_enricher_completed,with_seed_completed,with_state |
| __all__ | __all__ | bioetl.application.composite.column_orderer | 1 |  |
| class | ColumnOrderer | bioetl.application.composite.column_orderer | 388 | public=filter_by_layer_config,get_ordered_columns,group_columns,order_column_names,order_columns |
| function | _collect_pattern_columns | bioetl.application.composite.column_orderer | 38 | (available: set[str], used: set[str], group: ColumnGroupConfig, sort_fn: _SortFn, logger: LoggerPort) |
| __all__ | __all__ | bioetl.application.composite.column_renamer | 1 |  |
| class | ColumnRenamer | bioetl.application.composite.column_renamer | 147 | public=build_rename_map,rename_dataframe |
| class | EnrichmentCoordinator | bioetl.application.composite.coordinator | 383 | public=run_enrichers |
| class | EnricherDeduplicator | bioetl.application.composite.deduplication | 199 | public=deduplicate |
| class | DependencyCoordinator | bioetl.application.composite.dependency_coordinator | 370 | public=run_dependencies |
| __all__ | __all__ | bioetl.application.composite.fsm_helper | 1 |  |
| class | FSMStateHelper | bioetl.application.composite.fsm_helper | 195 | public=handle_resume_from_failed,log_fsm_transition,log_resume_context,validate_fsm_transition |
| class | KeyExtractorService | bioetl.application.composite.key_extractor | 128 | public=extract |
| class | MergeService | bioetl.application.composite.merger | 1831 | public=merge |
| function | _path_to_table_name | bioetl.application.composite.merger | 26 | (path: str) |
| class | CompositePreflightValidator | bioetl.application.composite.preflight_validator | 551 | public=log_resolved_field_sources,validate |
| class | FieldInfo | bioetl.application.composite.preflight_validator | 14 |  |
| class | PreflightValidationError | bioetl.application.composite.preflight_validator | 14 | bases=Exception |
| class | PreflightValidationResult | bioetl.application.composite.preflight_validator | 22 | public=errors,warnings |
| class | ValidationIssue | bioetl.application.composite.preflight_validator | 16 |  |
| type_alias | SchemaFields | bioetl.application.composite.preflight_validator | 1 |  |
| class | CompositePipelineRunner | bioetl.application.composite.runner | 993 | public=config,run,run_id |
| class | CompositeRuntimeConfig | bioetl.application.composite.runner | 38 |  |
| function | add_not_run_results | bioetl.application.composite.runner_helpers | 63 | (enrichment_results: dict[str, EnrichmentResult], enrichers_to_run: list[EnricherConfig], all_enrichers: Iterable[EnricherConfig], completed_enrichers: Set[str], required_only: bool, composite_name: str, logger: LoggerPort) |
| function | calculate_had_warnings | bioetl.application.composite.runner_helpers | 38 | (enrichment_results: dict[str, EnrichmentResult], required_enrichers: frozenset[str], composite_name: str, logger: LoggerPort) |
| function | get_mergeable_dependencies | bioetl.application.composite.runner_helpers | 54 | (dependency_results: dict[str, DependencyResult], all_dependencies: Iterable[DependencyConfig], logger: LoggerPort) |
| function | get_mergeable_enrichers | bioetl.application.composite.runner_helpers | 46 | (enrichment_results: dict[str, EnrichmentResult], all_enrichers: Iterable[EnricherConfig], logger: LoggerPort) |
| function | log_enrichment_summary | bioetl.application.composite.runner_helpers | 60 | (enrichment_results: dict[str, EnrichmentResult], composite_name: str, logger: LoggerPort) |
| __all__ | __all__ | bioetl.application.core.__init__ | 1 |  |
| class | BasePipeline | bioetl.application.core.base | 180 | bases=ABC; public=config,context,create,entity_type,limit,logger,pipeline_name,provider,resume,run_id,run_type,runtime,services,shutdown_signal,transform_bronze_to_silver,transformer |
| class | BaseTransformer | bioetl.application.core.base_transformer | 738 | bases=ABC; public=compute_content_hash,compute_entity_id,entity_to_silver_record,hash_pii_list,hash_pii_value,serialize_json,serialize_json_fields,serialize_json_list,should_write_gold,should_write_silver,transform,transform_for_gold,validate_value_object,validate_value_objects |
| class | TransformationError | bioetl.application.core.base_transformer | 17 | bases=Exception |
| class | ValueObjectWithFromRaw | bioetl.application.core.base_transformer | 16 | bases=Protocol[V]; public=from_raw,value |
| constant | T | bioetl.application.core.base_transformer | 1 |  |
| constant | V | bioetl.application.core.base_transformer | 1 |  |
| class | BatchExecutor | bioetl.application.core.batch_executor | 725 | public=entity_type,execute,get_dq_context,process |
| class | BatchResult | bioetl.application.core.batch_executor | 7 |  |
| class | BatchMetricsRecorder | bioetl.application.core.batch_metrics | 116 | public=track_batch_size,track_error,track_processed_records,track_quarantined_records |
| __all__ | __all__ | bioetl.application.core.batch_tracing | 1 |  |
| class | BatchTracingManager | bioetl.application.core.batch_tracing | 225 | public=end_span,end_span_with_shutdown,set_batch_result,set_execution_stats,set_transform_result,start_batch_span,start_execution_span,start_layer_span |
| class | BatchTransformer | bioetl.application.core.batch_transformer | 256 | public=transform_batch,transform_single,transform_stream |
| class | StreamingBatchProcessor | bioetl.application.core.batch_transformer | 86 | public=iter_records,process_in_chunks |
| class | TransformResult | bioetl.application.core.batch_transformer | 6 |  |
| class | TransformedRecord | bioetl.application.core.batch_transformer | 15 |  |
| class | BatchWriter | bioetl.application.core.batch_writer | 524 | public=log_and_track_write_error,write_bronze,write_gold,write_silver |
| class | CheckpointManager | bioetl.application.core.checkpoint_manager | 105 | public=delete_checkpoint,list_all,load_checkpoint,save_checkpoint |
| class | CleanupPreview | bioetl.application.core.cleanup_service | 12 |  |
| class | CleanupResult | bioetl.application.core.cleanup_service | 21 | public=total_cleared |
| class | CleanupService | bioetl.application.core.cleanup_service | 159 | public=execute,preview |
| class | LayerInfo | bioetl.application.core.cleanup_service | 12 |  |
| class | LockConfig | bioetl.application.core.config | 65 | public=for_pipeline |
| class | RecordProcessorConfig | bioetl.application.core.config | 17 |  |
| __all__ | __all__ | bioetl.application.core.dict_transformers | 1 |  |
| constant | T | bioetl.application.core.dict_transformers | 1 |  |
| function | _extract_nested_values | bioetl.application.core.dict_transformers | 9 | (items: list[dict[str, Any]], field: str) |
| function | aggregate_nested_lists | bioetl.application.core.dict_transformers | 46 | (items: list[dict[str, Any]] | None, field: str, deduplicate: bool = True) |
| function | extract_list_field | bioetl.application.core.dict_transformers | 46 | (items: list[dict[str, Any]] | None, field: str, converter: Callable[[Any], T] | None = None) |
| function | flatten_nested_dict | bioetl.application.core.dict_transformers | 58 | (data: dict[str, Any] | None, prefix: str, field_mapping: dict[str, Callable[[Any], Any] | None], renames: dict[str, str] | None = None) |
| function | normalize_string | bioetl.application.core.dict_transformers | 23 | (value: str | None) |
| function | parse_date_field | bioetl.application.core.dict_transformers | 27 | (value: str | None, fmt: str = '%Y-%m-%d') |
| function | safe_extract | bioetl.application.core.dict_transformers | 27 | (record: dict[str, Any], key: str, default: T | None = None) |
| function | validate_smiles | bioetl.application.core.dict_transformers | 28 | (smiles: str | None) |
| function | compute_publication_term_entity_id | bioetl.application.core.entity_id | 21 | (document_chembl_id: str, term_type: str, term: str) |
| __all__ | __all__ | bioetl.application.core.field_specs | 1 |  |
| class | FieldGroup | bioetl.application.core.field_specs | 23 |  |
| class | FieldSpec | bioetl.application.core.field_specs | 21 |  |
| constant | FLOAT | bioetl.application.core.field_specs | 1 |  |
| constant | INT | bioetl.application.core.field_specs | 1 |  |
| constant | PMID | bioetl.application.core.field_specs | 1 |  |
| constant | STR | bioetl.application.core.field_specs | 1 |  |
| function | float_fields | bioetl.application.core.field_specs | 13 | (*field_names: str) |
| function | int_fields | bioetl.application.core.field_specs | 13 | (*field_names: str) |
| function | map_field | bioetl.application.core.field_specs | 27 | (record: BronzeRecord, spec: FieldSpec) |
| function | map_field_group | bioetl.application.core.field_specs | 30 | (record: BronzeRecord, group: FieldGroup) |
| function | map_field_groups | bioetl.application.core.field_specs | 19 | (record: BronzeRecord, groups: Sequence[FieldGroup]) |
| function | map_fields | bioetl.application.core.field_specs | 32 | (record: BronzeRecord, specs: Sequence[FieldSpec]) |
| function | normalize_pmid | bioetl.application.core.field_specs | 30 | (value: Any) |
| function | pmid_fields | bioetl.application.core.field_specs | 16 | (*field_names: str) |
| function | simple_fields | bioetl.application.core.field_specs | 15 | (*field_names: str) |
| class | FilteredDataSource | bioetl.application.core.filtered_data_source | 348 | public=aclose,fetch,filter_result,get_source_metadata,health_check,provider_name |
| __all__ | __all__ | bioetl.application.core.heartbeat | 1 |  |
| class | HeartbeatTask | bioetl.application.core.heartbeat | 103 | public=is_running,start,stop |
| class | IDMappingDataSource | bioetl.application.core.idmapping_data_source | 258 | public=aclose,fetch,health_check |
| class | LockManager | bioetl.application.core.lock_manager | 253 | public=acquire,create,get_context,release,start_heartbeat,validate |
| __all__ | __all__ | bioetl.application.core.pipeline_services | 1 |  |
| class | PipelineServices | bioetl.application.core.pipeline_services | 110 | public=aclose |
| __all__ | __all__ | bioetl.application.core.postrun_service | 1 |  |
| class | ExecutorMetricsProtocol | bioetl.application.core.postrun_service | 11 | bases=Protocol |
| class | PostrunResult | bioetl.application.core.postrun_service | 12 |  |
| class | PostrunService | bioetl.application.core.postrun_service | 217 | public=cleanup,run,run_dq_checks,run_vacuum_if_enabled |
| __all__ | __all__ | bioetl.application.core.preflight_service | 1 |  |
| class | PreflightService | bioetl.application.core.preflight_service | 263 | public=validate_infrastructure,validate_medallion_config,validate_preflight,validate_write_modes |
| class | _HealthAggregator | bioetl.application.core.preflight_service | 227 | public=assert_healthy,check_all |
| class | _MedallionConfigValidator | bioetl.application.core.preflight_service | 265 | public=validate_medallion_config,validate_write_modes |
| class | GoldFilterCallback | bioetl.application.core.protocols | 6 | bases=Protocol |
| class | GoldTransformCallback | bioetl.application.core.protocols | 11 | bases=Protocol |
| class | TransformCallback | bioetl.application.core.protocols | 8 | bases=Protocol |
| class | TransformerPort | bioetl.application.core.protocols | 39 | bases=Protocol; public=transform |
| class | PublicationTermDataSource | bioetl.application.core.publication_term_data_source | 546 | public=aclose,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,health_check,provider_name |
| class | QuarantineManager | bioetl.application.core.quarantine_manager | 84 | public=get_stats,inspect,quarantine_record |
| class | RecordProcessor | bioetl.application.core.record_processor | 188 | public=process_batch |
| class | PipelineRunner | bioetl.application.core.runner | 152 | public=logger,run,services |
| __all__ | __all__ | bioetl.application.core.shutdown | 1 |  |
| class | ShutdownSignal | bioetl.application.core.shutdown | 93 | public=initiate_shutdown,is_requested,is_shutting_down,mark_completed,request,reset,wait,wait_for_completion |
| function | create_shutdown_service | bioetl.application.core.shutdown | 17 | (logger: LoggerPort, metrics: MetricsPort | None = None) |
| __all__ | __all__ | bioetl.application.core.subcellular_fraction_data_source | 1 |  |
| class | SubcellularFractionDataSource | bioetl.application.core.subcellular_fraction_data_source | 481 | public=aclose,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,health_check,provider_name |
| __all__ | __all__ | bioetl.application.observability.__init__ | 1 |  |
| class | LifecyclePhase | bioetl.application.observability.observer | 13 | bases=StrEnum |
| class | PipelineObserver | bioetl.application.observability.observer | 319 | bases=AbstractContextManager['PipelineObserver']; public=emit_dq_anomaly,emit_event,emit_health_check_result,emit_phase_completed,emit_phase_started,emit_vacuum_result |
| function | _span_context | bioetl.application.observability.span_helpers | 20 | (tracer: TracingPort, name: str, attributes: dict[str, Any] | None = None, tracer_name: str = 'bioetl') |
| function | traced_async_operation | bioetl.application.observability.span_helpers | 9 | (tracer: TracingPort, name: str, attributes: dict[str, Any] | None = None, tracer_name: str = 'bioetl') |
| __all__ | __all__ | bioetl.application.pipelines.__init__ | 1 |  |
| __all__ | __all__ | bioetl.application.pipelines.chembl.__init__ | 1 |  |
| class | ChEMBLActivityPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLAssayParametersPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLAssayPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLCellLinePipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLCompoundRecordPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLMoleculePipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLProteinClassPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLPublicationPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLPublicationSimilarityPipeline | bioetl.application.pipelines.chembl._pipelines | 6 | bases=BasePipeline |
| class | ChEMBLPublicationTermPipeline | bioetl.application.pipelines.chembl._pipelines | 6 | bases=BasePipeline |
| class | ChEMBLSubcellularFractionPipeline | bioetl.application.pipelines.chembl._pipelines | 6 | bases=BasePipeline |
| class | ChEMBLTargetComponentPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLTargetPipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ChEMBLTissuePipeline | bioetl.application.pipelines.chembl._pipelines | 2 | bases=BasePipeline |
| class | ActivityTransformer | bioetl.application.pipelines.chembl.activity_transformer | 75 | bases=BaseChemblTransformer |
| __all__ | __all__ | bioetl.application.pipelines.chembl.assay_parameters_transformer | 1 |  |
| class | AssayParametersTransformer | bioetl.application.pipelines.chembl.assay_parameters_transformer | 86 | bases=BaseChemblTransformer |
| constant | KNOWN_PARAM_TYPES | bioetl.application.pipelines.chembl.assay_parameters_transformer | 1 |  |
| class | AssayTransformer | bioetl.application.pipelines.chembl.assay_transformer | 39 | bases=BaseChemblTransformer |
| function | _extract_variant | bioetl.application.pipelines.chembl.assay_transformer | 15 | (data: dict[str, Any] | None) |
| class | BaseChemblTransformer | bioetl.application.pipelines.chembl.base_chembl_transformer | 153 | bases=BaseTransformer |
| class | CellLineTransformer | bioetl.application.pipelines.chembl.cell_line_transformer | 60 | bases=BaseChemblTransformer |
| class | CompoundRecordTransformer | bioetl.application.pipelines.chembl.compound_record_transformer | 61 | bases=BaseChemblTransformer |
| class | MoleculeTransformer | bioetl.application.pipelines.chembl.molecule_transformer | 68 | bases=BaseChemblTransformer |
| class | ProteinClassTransformer | bioetl.application.pipelines.chembl.protein_class_transformer | 31 | bases=BaseChemblTransformer |
| class | PublicationSimilarityTransformer | bioetl.application.pipelines.chembl.publication_similarity_transformer | 63 | bases=BaseChemblTransformer |
| class | PublicationTermTransformer | bioetl.application.pipelines.chembl.publication_term_transformer | 266 | bases=BaseChemblTransformer; public=compute_term_entity_id,extract_terms_from_document |
| class | PublicationTransformer | bioetl.application.pipelines.chembl.publication_transformer | 170 | bases=BaseChemblTransformer; public=entity_to_silver_record |
| __all__ | __all__ | bioetl.application.pipelines.chembl.subcellular_fraction_transformer | 1 |  |
| class | SubcellularFractionTransformer | bioetl.application.pipelines.chembl.subcellular_fraction_transformer | 164 | bases=BaseChemblTransformer; public=compute_fraction_entity_id,extract_fraction_from_assay |
| class | TargetComponentTransformer | bioetl.application.pipelines.chembl.target_component_transformer | 46 | bases=BaseChemblTransformer |
| class | TargetTransformer | bioetl.application.pipelines.chembl.target_transformer | 149 | bases=BaseChemblTransformer |
| class | TissueTransformer | bioetl.application.pipelines.chembl.tissue_transformer | 37 | bases=BaseChemblTransformer |
| __all__ | __all__ | bioetl.application.pipelines.common.__init__ | 1 |  |
| class | BasePublicationTransformer | bioetl.application.pipelines.common.base_publication_transformer | 210 | bases=BaseTransformer |
| function | extract_author_names | bioetl.application.pipelines.common.extractors | 68 | (items: list[dict[str, Any]] | None, name_field: str = 'name', nested_field: str | None = None) |
| __all__ | __all__ | bioetl.application.pipelines.crossref.__init__ | 1 |  |
| function | _build_author_detail | bioetl.application.pipelines.crossref.author_extractors | 19 | (author: dict[str, Any]) |
| function | _extract_author_affiliations_list | bioetl.application.pipelines.crossref.author_extractors | 13 | (author: dict[str, Any]) |
| function | _extract_author_sequence | bioetl.application.pipelines.crossref.author_extractors | 7 | (author: dict[str, Any]) |
| function | _normalize_orcid | bioetl.application.pipelines.crossref.author_extractors | 14 | (orcid_value: str | None) |
| function | extract_author_details | bioetl.application.pipelines.crossref.author_extractors | 19 | (publication: dict[str, Any]) |
| function | extract_author_orcids | bioetl.application.pipelines.crossref.author_extractors | 22 | (publication: dict[str, Any]) |
| __all__ | __all__ | bioetl.application.pipelines.crossref.extractors | 1 |  |
| function | extract_affiliations | bioetl.application.pipelines.crossref.extractors | 41 | (publication: dict[str, Any]) |
| function | extract_authors | bioetl.application.pipelines.crossref.extractors | 43 | (publication: dict[str, Any]) |
| function | extract_content_domain | bioetl.application.pipelines.crossref.extractors | 31 | (publication: dict[str, Any]) |
| function | extract_dates | bioetl.application.pipelines.crossref.extractors | 40 | (publication: dict[str, Any]) |
| function | extract_issn_by_type | bioetl.application.pipelines.crossref.extractors | 46 | (publication: dict[str, Any]) |
| function | extract_journal_info | bioetl.application.pipelines.crossref.extractors | 30 | (publication: dict[str, Any]) |
| function | extract_license_url | bioetl.application.pipelines.crossref.extractors | 27 | (publication: dict[str, Any]) |
| function | extract_page_info | bioetl.application.pipelines.crossref.extractors | 31 | (publication: dict[str, Any]) |
| function | extract_published_date | bioetl.application.pipelines.crossref.extractors | 27 | (publication: dict[str, Any]) |
| function | _clean_string | bioetl.application.pipelines.crossref.reference_extractors | 8 | (value: Any, lowercase: bool = False) |
| function | _parse_year | bioetl.application.pipelines.crossref.reference_extractors | 11 | (year_raw: Any) |
| function | extract_references | bioetl.application.pipelines.crossref.reference_extractors | 40 | (publication: dict[str, Any]) |
| class | CrossRefPublicationTransformer | bioetl.application.pipelines.crossref.transformer | 326 | bases=BasePublicationTransformer; public=entity_to_silver_record |
| __all__ | __all__ | bioetl.application.pipelines.generic | 1 |  |
| class | GenericPipeline | bioetl.application.pipelines.generic | 33 | bases=BasePipeline |
| __all__ | __all__ | bioetl.application.pipelines.openalex.__init__ | 1 |  |
| __all__ | __all__ | bioetl.application.pipelines.openalex.extractors | 1 |  |
| function | _extract_id_from_url | bioetl.application.pipelines.openalex.extractors | 12 | (url: str | None) |
| function | _extract_orcid_from_url | bioetl.application.pipelines.openalex.extractors | 24 | (url: str | None) |
| function | _get_nested_display_name | bioetl.application.pipelines.openalex.extractors | 12 | (obj: Any) |
| function | _parse_grant_dict | bioetl.application.pipelines.openalex.extractors | 21 | (grant: dict[str, Any]) |
| function | _parse_topic_dict | bioetl.application.pipelines.openalex.extractors | 24 | (topic: dict[str, Any]) |
| function | extract_affiliations | bioetl.application.pipelines.openalex.extractors | 15 | (authorships: list[dict[str, Any]]) |
| function | extract_author_ids | bioetl.application.pipelines.openalex.extractors | 19 | (authorships: list[dict[str, Any]]) |
| function | extract_author_orcids | bioetl.application.pipelines.openalex.extractors | 25 | (authorships: list[dict[str, Any]]) |
| function | extract_authors | bioetl.application.pipelines.openalex.extractors | 11 | (authorships: list[dict[str, Any]]) |
| function | extract_biblio_info | bioetl.application.pipelines.openalex.extractors | 15 | (biblio: dict[str, Any] | None) |
| function | extract_doi | bioetl.application.pipelines.openalex.extractors | 11 | (doi_url: str | None) |
| function | extract_external_ids | bioetl.application.pipelines.openalex.extractors | 22 | (ids: dict[str, Any] | None) |
| function | extract_grants | bioetl.application.pipelines.openalex.extractors | 14 | (grants: list[dict[str, Any]] | None) |
| function | extract_institution_country_codes | bioetl.application.pipelines.openalex.extractors | 22 | (authorships: list[dict[str, Any]]) |
| function | extract_institution_ids | bioetl.application.pipelines.openalex.extractors | 23 | (authorships: list[dict[str, Any]]) |
| function | extract_institution_ror_ids | bioetl.application.pipelines.openalex.extractors | 45 | (authorships: list[dict[str, Any]]) |
| function | extract_journal_info | bioetl.application.pipelines.openalex.extractors | 14 | (primary_location: dict[str, Any] | None) |
| function | extract_keywords | bioetl.application.pipelines.openalex.extractors | 14 | (keywords: list[dict[str, Any]] | None) |
| function | extract_mesh_terms | bioetl.application.pipelines.openalex.extractors | 17 | (mesh: list[dict[str, Any]] | None) |
| function | extract_open_access_info | bioetl.application.pipelines.openalex.extractors | 9 | (open_access: dict[str, Any] | None) |
| function | extract_openalex_id | bioetl.application.pipelines.openalex.extractors | 7 | (openalex_url: str | None) |
| function | extract_primary_topic | bioetl.application.pipelines.openalex.extractors | 7 | (primary_topic: dict[str, Any] | None) |
| function | extract_topics | bioetl.application.pipelines.openalex.extractors | 17 | (topics: list[dict[str, Any]] | None, max_count: int = 10) |
| function | reconstruct_abstract | bioetl.application.pipelines.openalex.extractors | 20 | (inverted_index: dict[str, list[int]] | None) |
| class | OpenAlexPublicationTransformer | bioetl.application.pipelines.openalex.transformer | 268 | bases=BasePublicationTransformer; public=entity_to_silver_record |
| __all__ | __all__ | bioetl.application.pipelines.pubchem.__init__ | 1 |  |
| class | PubChemCompoundPipeline | bioetl.application.pipelines.pubchem.__init__ | 5 | bases=BasePipeline |
| class | PubChemCompoundTransformer | bioetl.application.pipelines.pubchem.transformer | 168 | bases=BaseTransformer |
| __all__ | __all__ | bioetl.application.pipelines.pubmed.__init__ | 1 |  |
| class | PubMedPublicationPipeline | bioetl.application.pipelines.pubmed.__init__ | 5 | bases=BasePipeline |
| __all__ | __all__ | bioetl.application.pipelines.pubmed.extractors.__init__ | 1 |  |
| class | AbstractExtractor | bioetl.application.pipelines.pubmed.extractors.abstract | 88 | bases=BaseFieldExtractor; public=extract,extract_abstract,is_abstract_structured,normalize |
| class | AuthorExtractor | bioetl.application.pipelines.pubmed.extractors.author | 246 | bases=BaseFieldExtractor; public=extract,normalize,parse_affiliations,parse_authors,parse_structured_affiliations,process |
| class | RawAuthor | bioetl.application.pipelines.pubmed.extractors.author | 9 | bases=TypedDict |
| class | StructuredAffiliation | bioetl.application.pipelines.pubmed.extractors.author | 21 | bases=TypedDict |
| constant | EMAIL_PATTERN | bioetl.application.pipelines.pubmed.extractors.author | 1 |  |
| class | BaseFieldExtractor | bioetl.application.pipelines.pubmed.extractors.base | 53 | bases=ABC; public=extract,normalize,process |
| class | ClassificationExtractor | bioetl.application.pipelines.pubmed.extractors.classification | 230 | bases=BaseFieldExtractor; public=extract,normalize,parse_chemicals,parse_databanks,parse_gene_symbols,parse_keywords,parse_mesh_terms,parse_publication_types |
| class | NormalizedClassification | bioetl.application.pipelines.pubmed.extractors.classification | 6 | bases=TypedDict |
| class | RawClassification | bioetl.application.pipelines.pubmed.extractors.classification | 6 | bases=TypedDict |
| class | DateExtractor | bioetl.application.pipelines.pubmed.extractors.date | 198 | bases=BaseFieldExtractor; public=extract,extract_article_date,extract_date,extract_history_date,format_date,normalize |
| class | MedlineDateParser | bioetl.application.pipelines.pubmed.extractors.date | 137 | public=parse |
| class | NormalizedDate | bioetl.application.pipelines.pubmed.extractors.date | 5 | bases=TypedDict |
| class | RawDate | bioetl.application.pipelines.pubmed.extractors.date | 6 | bases=TypedDict |
| class | AllArticleIds | bioetl.application.pipelines.pubmed.extractors.identifier | 23 | bases=TypedDict |
| class | ArticleIdentifiers | bioetl.application.pipelines.pubmed.extractors.identifier | 5 | bases=TypedDict |
| class | ELocationIds | bioetl.application.pipelines.pubmed.extractors.identifier | 10 | bases=TypedDict |
| class | IdentifierExtractor | bioetl.application.pipelines.pubmed.extractors.identifier | 269 | bases=BaseFieldExtractor; public=extract,extract_doi,extract_elocation_ids,extract_mid,extract_pii,extract_pmc_id,extract_publisher_id,normalize,parse_all_article_ids |
| class | PubMedPublicationTransformer | bioetl.application.pipelines.pubmed.transformer | 694 | bases=BasePublicationTransformer; public=entity_to_silver_record |
| function | get_int | bioetl.application.pipelines.pubmed.xml_parser | 36 | (node: ET.Element | None) |
| function | get_text | bioetl.application.pipelines.pubmed.xml_parser | 28 | (node: ET.Element | None) |
| __all__ | __all__ | bioetl.application.pipelines.semanticscholar.__init__ | 1 |  |
| function | extract_affiliations | bioetl.application.pipelines.semanticscholar._author_extractors | 30 | (authors: list[dict[str, Any]] | None) |
| function | extract_author_h_indices | bioetl.application.pipelines.semanticscholar._author_extractors | 33 | (authors: list[dict[str, Any]] | None) |
| function | extract_author_ids | bioetl.application.pipelines.semanticscholar._author_extractors | 23 | (authors: list[dict[str, Any]] | None) |
| function | extract_author_orcids | bioetl.application.pipelines.semanticscholar._author_extractors | 37 | (authors: list[dict[str, Any]] | None) |
| function | extract_author_s2_ids | bioetl.application.pipelines.semanticscholar._author_extractors | 31 | (authors: list[dict[str, Any]] | None) |
| function | extract_authors | bioetl.application.pipelines.semanticscholar._author_extractors | 29 | (authors: list[dict[str, Any]] | None) |
| __all__ | __all__ | bioetl.application.pipelines.semanticscholar._page_parsing | 1 |  |
| function | parse_volume_issue | bioetl.application.pipelines.semanticscholar._page_parsing | 38 | (volume_str: str | None) |
| __all__ | __all__ | bioetl.application.pipelines.semanticscholar.extractors | 1 |  |
| constant | OA_STATUS_SET | bioetl.application.pipelines.semanticscholar.extractors | 1 |  |
| function | extract_citation_contexts | bioetl.application.pipelines.semanticscholar.extractors | 42 | (citations: list[dict[str, Any]] | None, max_contexts: int = 100) |
| function | extract_external_ids | bioetl.application.pipelines.semanticscholar.extractors | 28 | (external_ids: dict[str, Any] | None) |
| function | extract_fields_of_study | bioetl.application.pipelines.semanticscholar.extractors | 28 | (fields_of_study: list[str] | None, max_count: int = 10) |
| function | extract_journal_info | bioetl.application.pipelines.semanticscholar.extractors | 54 | (journal: dict[str, Any] | None, venue: str | None) |
| function | extract_open_access_info | bioetl.application.pipelines.semanticscholar.extractors | 61 | (is_open_access: bool | None, open_access_pdf: dict[str, Any] | None) |
| function | extract_tldr | bioetl.application.pipelines.semanticscholar.extractors | 18 | (tldr: dict[str, Any] | None) |
| function | normalize_oa_status | bioetl.application.pipelines.semanticscholar.extractors | 27 | (status: str | None) |
| class | SemanticScholarPublicationTransformer | bioetl.application.pipelines.semanticscholar.transformer | 248 | bases=BasePublicationTransformer; public=entity_to_silver_record |
| __all__ | __all__ | bioetl.application.pipelines.uniprot.__init__ | 1 |  |
| class | UniProtProteinPipeline | bioetl.application.pipelines.uniprot.__init__ | 5 | bases=BasePipeline |
| __all__ | __all__ | bioetl.application.pipelines.uniprot.extractors.__init__ | 1 |  |
| class | CommentExtractor | bioetl.application.pipelines.uniprot.extractors.comments | 346 | public=count_isoforms,extract_alternative_products,extract_biophysicochemical_properties,extract_by_type,extract_catalytic_activity,extract_cofactors,extract_induction,extract_isoform_details,extract_reaction_ec_numbers,extract_reactions,extract_subcellular_locations,extract_text_values |
| function | _build_isoform_data | bioetl.application.pipelines.uniprot.extractors.comments | 17 | (iso: dict[str, Any]) |
| function | _extract_absorption_data | bioetl.application.pipelines.uniprot.extractors.comments | 9 | (absorption: dict[str, Any]) |
| function | _extract_biophys_from_comment | bioetl.application.pipelines.uniprot.extractors.comments | 38 | (comment: dict[str, Any]) |
| function | _extract_cofactor_entry | bioetl.application.pipelines.uniprot.extractors.comments | 27 | (cofactor: dict[str, Any]) |
| function | _extract_kinetic_parameters | bioetl.application.pipelines.uniprot.extractors.comments | 21 | (kinetics: dict[str, Any]) |
| function | _extract_km_entry | bioetl.application.pipelines.uniprot.extractors.comments | 10 | (km: dict[str, Any]) |
| function | _extract_list_entries | bioetl.application.pipelines.uniprot.extractors.comments | 9 | (data_list: Any, extractor: Any) |
| function | _extract_location_value | bioetl.application.pipelines.uniprot.extractors.comments | 15 | (loc: dict[str, Any]) |
| function | _extract_reaction_data | bioetl.application.pipelines.uniprot.extractors.comments | 15 | (reaction: dict[str, Any]) |
| function | _extract_texts_from_dict | bioetl.application.pipelines.uniprot.extractors.comments | 17 | (data: dict[str, Any] | None) |
| function | _extract_vmax_entry | bioetl.application.pipelines.uniprot.extractors.comments | 10 | (vmax: dict[str, Any]) |
| function | _is_comment_of_type | bioetl.application.pipelines.uniprot.extractors.comments | 11 | (comment: Any, comment_type: str) |
| class | CrossRefExtractor | bioetl.application.pipelines.uniprot.extractors.crossrefs | 366 | public=extract_cellular_component,extract_go_by_aspect,extract_go_terms,extract_interpro_xrefs,extract_molecular_function,extract_pdb_xrefs,extract_pfam_xrefs,extract_reactome_xrefs,extract_xref_ids |
| class | FeatureExtractor | bioetl.application.pipelines.uniprot.extractors.features | 328 | public=extract_acetylation,extract_active_sites,extract_binding_sites,extract_disulfide_bonds,extract_domains,extract_features,extract_features_by_type,extract_glycosylation,extract_intramembrane,extract_keywords,extract_lipidation,extract_modified_residues,extract_phosphorylation,extract_propeptide,extract_ptm_by_pattern,extract_signal_peptide,extract_topology,extract_transmembrane,extract_ubiquitination |
| function | _build_feature_dict | bioetl.application.pipelines.uniprot.extractors.features | 22 | (feature: dict[str, Any]) |
| function | _build_keyword_dict | bioetl.application.pipelines.uniprot.extractors.features | 17 | (kw: dict[str, Any]) |
| function | _extract_feature_location | bioetl.application.pipelines.uniprot.extractors.features | 15 | (location: dict[str, Any], feature_data: dict[str, Any]) |
| class | GeneExtractor | bioetl.application.pipelines.uniprot.extractors.genes | 104 | public=extract_gene_names,extract_gene_orf_names,extract_gene_synonyms,extract_primary_gene |
| class | TaxonomyExtractor | bioetl.application.pipelines.uniprot.extractors.taxonomy | 112 | public=extract_all,extract_genus,extract_phylum,extract_superkingdom |
| class | ExtractorUtils | bioetl.application.pipelines.uniprot.extractors.utils | 167 | public=count_list,extract_alternative_names,extract_ec_numbers,extract_protein_existence,extract_short_names,is_reviewed,parse_uniprot_date,serialize_list |
| class | IDMappingTransformer | bioetl.application.pipelines.uniprot.idmapping_transformer | 128 | bases=BaseTransformer |
| class | UniProtProteinTransformer | bioetl.application.pipelines.uniprot.transformer | 370 | bases=BaseTransformer |
| __all__ | __all__ | bioetl.application.services.__init__ | 1 |  |
| class | BronzeCleanupService | bioetl.application.services.bronze_cleanup_service | 101 | public=aclose,cleanup,format_bytes |
| class | CleanupResult | bioetl.application.services.bronze_cleanup_service | 16 |  |
| class | CheckpointInfo | bioetl.application.services.checkpoint_service | 12 |  |
| class | CheckpointService | bioetl.application.services.checkpoint_service | 116 | public=aclose,delete_checkpoint,get_checkpoint,list_checkpoints |
| class | ConfigService | bioetl.application.services.config_service | 173 | public=get_pipeline_yaml_config,get_settings,list_pipelines,load_pipeline_config,validate_pipeline_config |
| class | PipelineInfo | bioetl.application.services.config_service | 16 |  |
| class | SettingsInfo | bioetl.application.services.config_service | 32 |  |
| __all__ | __all__ | bioetl.application.services.data_quality_service | 1 |  |
| class | DataQualityService | bioetl.application.services.data_quality_service | 260 | public=evaluate |
| __all__ | __all__ | bioetl.application.services.dq.__init__ | 1 |  |
| constant | FRESHNESS_CRITICAL_HOURS | bioetl.application.services.dq._checks_basic | 1 |  |
| constant | FRESHNESS_WARNING_HOURS | bioetl.application.services.dq._checks_basic | 1 |  |
| function | check_completeness | bioetl.application.services.dq._checks_basic | 38 | (df: pl.DataFrame, required_fields: list[str], threshold: float) |
| function | check_data_freshness | bioetl.application.services.dq._checks_basic | 44 | (df: pl.DataFrame, current_time: datetime) |
| function | check_record_count | bioetl.application.services.dq._checks_basic | 23 | (df: pl.DataFrame, baseline_stats: dict[str, object] | None) |
| function | _check_in_list_rule | bioetl.application.services.dq._checks_business | 8 | (df: pl.DataFrame, column: str, allowed: list[Any]) |
| function | _check_not_null_rule | bioetl.application.services.dq._checks_business | 4 | (df: pl.DataFrame, column: str) |
| function | _check_range_rule | bioetl.application.services.dq._checks_business | 14 | (df: pl.DataFrame, column: str, min_val: Any | None, max_val: Any | None) |
| function | _check_regex_rule | bioetl.application.services.dq._checks_business | 8 | (df: pl.DataFrame, column: str, pattern: str) |
| function | _evaluate_single_rule | bioetl.application.services.dq._checks_business | 19 | (df: pl.DataFrame, rule: dict[str, Any]) |
| function | check_business_rules | bioetl.application.services.dq._checks_business | 49 | (df: pl.DataFrame, rules: list[dict[str, Any]]) |
| function | check_referential_integrity | bioetl.application.services.dq._checks_integrity | 72 | (df: pl.DataFrame, reference_tables: dict[str, pl.DataFrame | pa.Table]) |
| function | check_scd_integrity | bioetl.application.services.dq._checks_integrity | 77 | (df: pl.DataFrame, scd_config: dict[str, Any] | None) |
| constant | NULL_RATE_CRITICAL_MULTIPLIER | bioetl.application.services.dq._checks_statistical | 1 |  |
| constant | NULL_RATE_WARNING_MULTIPLIER | bioetl.application.services.dq._checks_statistical | 1 |  |
| constant | RECORD_COUNT_CRITICAL_THRESHOLD | bioetl.application.services.dq._checks_statistical | 1 |  |
| constant | RECORD_COUNT_WARNING_THRESHOLD | bioetl.application.services.dq._checks_statistical | 1 |  |
| function | check_anomaly_detection | bioetl.application.services.dq._checks_statistical | 82 | (df: pl.DataFrame, baseline_stats: dict[str, Any] | None) |
| function | check_statistical_profile | bioetl.application.services.dq._checks_statistical | 74 | (df: pl.DataFrame, baseline_stats: dict[str, Any] | None) |
| __all__ | __all__ | bioetl.application.services.dq.bronze_analyzer | 1 |  |
| class | BronzeDQAnalyzer | bioetl.application.services.dq.bronze_analyzer | 211 | public=analyze |
| __all__ | __all__ | bioetl.application.services.dq.dq_report_builders | 1 |  |
| function | build_summary | bioetl.application.services.dq.dq_report_builders | 32 | (passed: int, failed: int, warnings: int, threshold_status: DQCheckStatus | None = None) |
| function | convert_value | bioetl.application.services.dq.dq_report_builders | 25 | (value: Any) |
| function | update_counts | bioetl.application.services.dq.dq_report_builders | 22 | (status: DQCheckStatus, passed: int, failed: int, warnings: int) |
| __all__ | __all__ | bioetl.application.services.dq.gold_analyzer | 1 |  |
| class | GoldDQAnalyzer | bioetl.application.services.dq.gold_analyzer | 143 | public=analyze |
| __all__ | __all__ | bioetl.application.services.dq.silver_analyzer | 1 |  |
| class | SilverDQAnalyzer | bioetl.application.services.dq.silver_analyzer | 532 | public=analyze |
| __all__ | __all__ | bioetl.application.services.dq_report_service | 1 |  |
| class | DQReportContext | bioetl.application.services.dq_report_service | 72 |  |
| class | DQReportResult | bioetl.application.services.dq_report_service | 40 | public=any_generated,reports_count |
| class | DQReportService | bioetl.application.services.dq_report_service | 407 | public=generate_reports,is_any_report_enabled |
| class | ColumnInfo | bioetl.application.services.export_service | 12 |  |
| class | ExportOptions | bioetl.application.services.export_service | 14 |  |
| class | ExportResult | bioetl.application.services.export_service | 23 | public=success |
| class | ExportService | bioetl.application.services.export_service | 200 | public=export,list_tables,preview |
| class | TableInfo | bioetl.application.services.export_service | 12 |  |
| class | TablePreview | bioetl.application.services.export_service | 16 |  |
| function | _scan_layer_for_tables | bioetl.application.services.export_service | 20 | (base_path: Path, layer_name: str) |
| function | _scan_provider_for_tables | bioetl.application.services.export_service | 20 | (provider_dir: Path, layer_name: str) |
| function | _write_delimited_file | bioetl.application.services.export_service | 21 | (table: pa.Table, output_path: Path, delimiter: str = ',') |
| function | _write_xlsx_file | bioetl.application.services.export_service | 26 | (table: pa.Table, output_path: Path) |
| class | DataSourceFactoryPort | bioetl.application.services.health_service | 15 | bases=Protocol; public=create,list_providers |
| class | HealthCheckSummary | bioetl.application.services.health_service | 26 | public=healthy_count,to_dict,unhealthy_count |
| class | HealthResult | bioetl.application.services.health_service | 46 | public=is_degraded,is_healthy,is_unhealthy,to_dict |
| class | HealthService | bioetl.application.services.health_service | 120 | public=check_providers,list_available_providers |
| class | LockInfo | bioetl.application.services.lock_service | 12 |  |
| class | LockService | bioetl.application.services.lock_service | 163 | public=aclose,check_lock,force_release_all,list_locks,release_lock |
| __all__ | __all__ | bioetl.application.services.medallion_lifecycle | 1 |  |
| class | MedallionLifecycleService | bioetl.application.services.medallion_lifecycle | 356 | public=archive,clear,finalize_run,prepare_for_run,vacuum |
| class | ClearResult | bioetl.application.services.medallion_types | 21 | public=total_cleared |
| class | PrepareResult | bioetl.application.services.medallion_types | 12 |  |
| class | VacuumResult | bioetl.application.services.medallion_types | 12 |  |
| __all__ | __all__ | bioetl.application.services.metrics_service | 1 |  |
| class | MetricsServerPort | bioetl.application.services.metrics_service | 34 | bases=Protocol; public=is_running,reset,start |
| class | MetricsServerStatus | bioetl.application.services.metrics_service | 14 |  |
| class | MetricsService | bioetl.application.services.metrics_service | 117 | public=get_status,is_running,start |
| class | StartResult | bioetl.application.services.metrics_service | 14 |  |
| class | PipelineNotFoundError | bioetl.application.services.pipeline_runner_service | 7 | bases=ValueError |
| class | PipelineRunResult | bioetl.application.services.pipeline_runner_service | 14 | bases=StrEnum |
| class | PipelineRunnerService | bioetl.application.services.pipeline_runner_service | 289 | public=list_pipelines,run,validate_pipeline |
| class | RunOptions | bioetl.application.services.pipeline_runner_service | 50 |  |
| class | RunResult | bioetl.application.services.pipeline_runner_service | 60 | public=duration_seconds,is_success,success_rate |
| class | QuarantineRecord | bioetl.application.services.quarantine_service | 18 |  |
| class | QuarantineService | bioetl.application.services.quarantine_service | 243 | public=aclose,get_stats,inspect,mark_as_reprocessed,purge,replay,update_status |
| __all__ | __all__ | bioetl.application.services.shutdown_service | 1 |  |
| class | PipelineShutdownError | bioetl.application.services.shutdown_service | 25 | bases=Exception |
| class | ShutdownReason | bioetl.application.services.shutdown_service | 10 | bases=Enum |
| class | ShutdownService | bioetl.application.services.shutdown_service | 207 | public=initiate_shutdown,is_shutting_down,mark_completed,reason,request,reset,wait,wait_for_completion |
| class | TableVacuumResult | bioetl.application.services.vacuum_service | 19 | public=success |
| class | VacuumAllResult | bioetl.application.services.vacuum_service | 27 | public=failed_tables,success_count,total_files_removed |
| class | VacuumService | bioetl.application.services.vacuum_service | 139 | public=collect_tables,vacuum_all,vacuum_table |
| type_alias | TableCollectorPort | bioetl.application.services.vacuum_service | 1 |  |

### 1.3 Infrastructure Layer
| Type | Name | Module | LOC | Details |
|------|------|--------|-----|---------|
| __all__ | __all__ | bioetl.infrastructure.adapters.__init__ | 1 |  |
| class | BaseHttpAdapter | bioetl.infrastructure.adapters.base | 89 | bases=HealthCheckProviderMixin,DataSourcePort; public=aclose |
| class | AdapterMetrics | bioetl.infrastructure.adapters.base_metrics | 103 | public=measure_request,record_batch_size,record_dropped_duplicates |
| class | CachedBronzeDataSource | bioetl.infrastructure.adapters.cached_bronze_data_source | 225 | public=aclose,fetch,health_check,provider_name |
| __all__ | __all__ | bioetl.infrastructure.adapters.chembl.__init__ | 1 |  |
| class | ChemblAdapter | bioetl.infrastructure.adapters.chembl.client | 1082 | bases=BaseHttpAdapter; public=clear_request_collector,effective_batch_size,fetch,fetch_as_models,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_entity_count,get_error_stats,get_source_metadata,request_count,reset_circuit_breaker |
| constant | CHEMBL_DTO_MODELS | bioetl.infrastructure.adapters.chembl.client | 1 |  |
| class | ChemblEntityMapper | bioetl.infrastructure.adapters.chembl.entity_mapper | 215 | public=get_dedup_key_fields,get_direct_record_url,get_plural_key,get_primary_key_field,get_resource_name,get_resource_url,has_composite_key,is_known_entity |
| constant | CHEMBL_API_BASE | bioetl.infrastructure.adapters.chembl.entity_mapper | 1 |  |
| constant | CHEMBL_STATUS_URL | bioetl.infrastructure.adapters.chembl.entity_mapper | 1 |  |
| constant | ENTITY_MAPPING | bioetl.infrastructure.adapters.chembl.entity_mapper | 1 |  |
| class | ActionType | bioetl.infrastructure.adapters.chembl.models | 8 | bases=BaseModel |
| class | ChemblActivityRecord | bioetl.infrastructure.adapters.chembl.models | 136 | bases=BaseModel |
| class | ChemblActivityResponse | bioetl.infrastructure.adapters.chembl.models | 14 | bases=BaseModel |
| class | ChemblAssayRecord | bioetl.infrastructure.adapters.chembl.models | 55 | bases=BaseModel |
| class | ChemblAssayResponse | bioetl.infrastructure.adapters.chembl.models | 11 | bases=BaseModel |
| class | ChemblCellLineRecord | bioetl.infrastructure.adapters.chembl.models | 20 | bases=BaseModel |
| class | ChemblCellLineResponse | bioetl.infrastructure.adapters.chembl.models | 11 | bases=BaseModel |
| class | ChemblMoleculeRecord | bioetl.infrastructure.adapters.chembl.models | 54 | bases=BaseModel |
| class | ChemblMoleculeResponse | bioetl.infrastructure.adapters.chembl.models | 11 | bases=BaseModel |
| class | ChemblPageMeta | bioetl.infrastructure.adapters.chembl.models | 10 | bases=BaseModel |
| class | ChemblPublicationApiRecord | bioetl.infrastructure.adapters.chembl.models | 47 | bases=BaseModel |
| class | ChemblPublicationResponse | bioetl.infrastructure.adapters.chembl.models | 15 | bases=BaseModel |
| class | ChemblReleaseInfo | bioetl.infrastructure.adapters.chembl.models | 14 | bases=BaseModel |
| class | ChemblTargetComponentRecord | bioetl.infrastructure.adapters.chembl.models | 26 | bases=BaseModel |
| class | ChemblTargetComponentResponse | bioetl.infrastructure.adapters.chembl.models | 11 | bases=BaseModel |
| class | ChemblTargetRecord | bioetl.infrastructure.adapters.chembl.models | 18 | bases=BaseModel |
| class | ChemblTargetResponse | bioetl.infrastructure.adapters.chembl.models | 11 | bases=BaseModel |
| class | LigandEfficiency | bioetl.infrastructure.adapters.chembl.models | 9 | bases=BaseModel |
| class | MoleculeHierarchy | bioetl.infrastructure.adapters.chembl.models | 8 | bases=BaseModel |
| class | MoleculeProperties | bioetl.infrastructure.adapters.chembl.models | 28 | bases=BaseModel |
| class | MoleculeStructures | bioetl.infrastructure.adapters.chembl.models | 9 | bases=BaseModel |
| constant | CHEMBL_RECORD_MODELS | bioetl.infrastructure.adapters.chembl.models | 1 |  |
| constant | CHEMBL_RESPONSE_MODELS | bioetl.infrastructure.adapters.chembl.models | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.adapters.common.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.adapters.common.api_request_collector | 1 |  |
| class | APIRequestCollector | bioetl.infrastructure.adapters.common.api_request_collector | 269 | public=clear,record_from_response,record_request,request_count,to_source_metadata |
| class | BaseTitleFallbackHandler | bioetl.infrastructure.adapters.common.base_title_fallback | 314 | bases=ABC; public=process_missing_dois,process_title_only_entries |
| function | normalize_title | bioetl.infrastructure.adapters.common.title_matching | 19 | (title: str) |
| function | titles_match | bioetl.infrastructure.adapters.common.title_matching | 52 | (query_title: str, found_title: str, threshold: float = 0.8, method: str = 'substring') |
| __all__ | __all__ | bioetl.infrastructure.adapters.crossref.__init__ | 1 |  |
| class | DoiBatchProcessor | bioetl.infrastructure.adapters.crossref.batch | 159 | public=fetch_batch,fetch_single |
| class | SearchPaginator | bioetl.infrastructure.adapters.crossref.batch | 120 | public=search |
| class | CrossRefAdapter | bioetl.infrastructure.adapters.crossref.client | 361 | bases=BaseHttpAdapter; public=aclose,clear_request_collector,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,request_count |
| constant | CROSSREF_API_BASE | bioetl.infrastructure.adapters.crossref.client | 1 |  |
| function | _create_crossref_adapter | bioetl.infrastructure.adapters.crossref.client | 45 | (http_client: UnifiedHTTPClient | None, logger: LoggerPort | None, settings: Settings | None, **kwargs: Any) |
| __all__ | __all__ | bioetl.infrastructure.adapters.crossref.exceptions | 1 |  |
| class | CrossRefApiError | bioetl.infrastructure.adapters.crossref.exceptions | 31 | bases=ExternalServiceError |
| class | CrossRefNotFoundError | bioetl.infrastructure.adapters.crossref.exceptions | 21 | bases=CrossRefApiError |
| class | CrossRefRateLimitError | bioetl.infrastructure.adapters.crossref.exceptions | 23 | bases=CrossRefApiError |
| class | CrossRefServiceUnavailableError | bioetl.infrastructure.adapters.crossref.exceptions | 20 | bases=CrossRefApiError |
| __all__ | __all__ | bioetl.infrastructure.adapters.crossref.fallback | 1 |  |
| class | TitleFallbackHandler | bioetl.infrastructure.adapters.crossref.fallback | 71 | bases=BaseTitleFallbackHandler; public=search_by_title |
| class | CrossRefAssertion | bioetl.infrastructure.adapters.crossref.models | 9 | bases=BaseModel |
| class | CrossRefAuthor | bioetl.infrastructure.adapters.crossref.models | 23 | bases=BaseModel |
| class | CrossRefClinicalTrial | bioetl.infrastructure.adapters.crossref.models | 10 | bases=BaseModel |
| class | CrossRefDateParts | bioetl.infrastructure.adapters.crossref.models | 14 | bases=BaseModel |
| class | CrossRefFunder | bioetl.infrastructure.adapters.crossref.models | 11 | bases=BaseModel |
| class | CrossRefLicense | bioetl.infrastructure.adapters.crossref.models | 13 | bases=BaseModel |
| class | CrossRefLink | bioetl.infrastructure.adapters.crossref.models | 15 | bases=BaseModel |
| class | CrossRefMessage | bioetl.infrastructure.adapters.crossref.models | 26 | bases=BaseModel |
| class | CrossRefPublicationRecord | bioetl.infrastructure.adapters.crossref.models | 166 | bases=BaseModel |
| class | CrossRefPublicationResponse | bioetl.infrastructure.adapters.crossref.models | 11 | bases=BaseModel |
| class | CrossRefPublicationsResponse | bioetl.infrastructure.adapters.crossref.models | 11 | bases=BaseModel |
| class | CrossRefReference | bioetl.infrastructure.adapters.crossref.models | 26 | bases=BaseModel |
| constant | CROSSREF_RECORD_MODELS | bioetl.infrastructure.adapters.crossref.models | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.adapters.decorators.__init__ | 1 |  |
| function | wrap_with_resilience | bioetl.infrastructure.adapters.decorators.__init__ | 59 | (data_source: DataSourcePort, retry_config: RetryConfig | None = None, circuit_breaker: CircuitBreakerPort | None = None, logger: LoggerPort | None = None, metrics: MetricsPort | None = None) |
| class | CircuitBreakerDataSourceDecorator | bioetl.infrastructure.adapters.decorators.circuit_breaker | 229 | public=aclose,fetch,get_circuit_state,get_failure_count,health_check,provider_name,reset_circuit |
| class | RetryingDataSourceDecorator | bioetl.infrastructure.adapters.decorators.retry | 259 | public=aclose,fetch,health_check,provider_name |
| __all__ | __all__ | bioetl.infrastructure.adapters.error_handling | 1 |  |
| class | AdapterErrorContext | bioetl.infrastructure.adapters.error_handling | 25 |  |
| class | ErrorCategory | bioetl.infrastructure.adapters.error_handling | 17 | bases=StrEnum |
| class | ErrorService | bioetl.infrastructure.adapters.error_handling | 480 | public=classify_exception,classify_http_error,get_error_type,get_retry_after,handle_error,log_error,should_retry,should_retry_status,wrap_error |
| class | DelegatingFallbackMixin | bioetl.infrastructure.adapters.filterable_mixin | 48 | public=fetch_filtered_with_fallback |
| class | FilterableStubMixin | bioetl.infrastructure.adapters.filterable_mixin | 21 | bases=NotSupportedMultiFilterMixin,DelegatingFallbackMixin |
| class | HasFetchFiltered | bioetl.infrastructure.adapters.filterable_mixin | 12 | bases=Protocol; public=fetch_filtered |
| class | NotSupportedMultiFilterMixin | bioetl.infrastructure.adapters.filterable_mixin | 47 | public=fetch_multi_filtered |
| class | HealthCheckContext | bioetl.infrastructure.adapters.health_check_mixin | 20 | public=elapsed_seconds |
| class | HealthCheckMixin | bioetl.infrastructure.adapters.health_check_mixin | 148 |  |
| class | HealthCheckProviderMixin | bioetl.infrastructure.adapters.health_check_mixin | 172 | bases=HealthCheckMixin; public=check_health,health_check |
| __all__ | __all__ | bioetl.infrastructure.adapters.http.__init__ | 1 |  |
| class | CircuitBreaker | bioetl.infrastructure.adapters.http.circuit_breaker | 169 | public=call,force_open,get_failure_count,get_state,get_trips_total,reset |
| constant | METRIC_CIRCUIT_BREAKER_STATE | bioetl.infrastructure.adapters.http.circuit_breaker | 1 |  |
| constant | METRIC_CIRCUIT_BREAKER_TRIPS | bioetl.infrastructure.adapters.http.circuit_breaker | 1 |  |
| constant | P | bioetl.infrastructure.adapters.http.circuit_breaker | 1 |  |
| constant | T | bioetl.infrastructure.adapters.http.circuit_breaker | 1 |  |
| function | is_circuit_breaker_error | bioetl.infrastructure.adapters.http.circuit_breaker | 18 | (exc: Exception) |
| __all__ | __all__ | bioetl.infrastructure.adapters.http.client | 1 |  |
| class | UnifiedHTTPClient | bioetl.infrastructure.adapters.http.client | 437 | public=get,get_once,head,post |
| function | assess_health_from_circuit_breaker | bioetl.infrastructure.adapters.http.health | 51 | (circuit_breaker: Any) |
| class | HealthAdjustedConfig | bioetl.infrastructure.adapters.http.health_monitor | 48 | public=apply_batch_size,apply_timeout |
| class | ProviderHealthMonitor | bioetl.infrastructure.adapters.http.health_monitor | 243 | public=get_adaptive_params,get_adjusted_config,get_all_states,get_state,record_error,record_health_check_result,record_success,update_from_health_check_result |
| class | ProviderHealthState | bioetl.infrastructure.adapters.http.health_monitor | 18 |  |
| class | ProviderHealthTracker | bioetl.infrastructure.adapters.http.health_monitor | 120 | public=consecutive_failures,get_adjusted_config,is_healthy,is_unhealthy,record_error,record_success,should_pause_pipeline,status,update |
| class | PaginatedFetcherMixin | bioetl.infrastructure.adapters.http.pagination | 46 | public=paginated_fetch |
| constant | T | bioetl.infrastructure.adapters.http.pagination | 1 |  |
| class | TokenBucket | bioetl.infrastructure.adapters.http.rate_limiter | 121 | public=acquire,available_tokens,try_acquire |
| function | create_pubchem_bucket | bioetl.infrastructure.adapters.http.rate_limiter | 10 | (metrics: MetricsPort | None = None) |
| function | create_pubmed_bucket | bioetl.infrastructure.adapters.http.rate_limiter | 15 | (with_api_key: bool = False, metrics: MetricsPort | None = None) |
| __all__ | __all__ | bioetl.infrastructure.adapters.input.__init__ | 1 |  |
| class | CsvFilterReader | bioetl.infrastructure.adapters.input.csv_filter_reader | 256 | public=load_filter_ids,load_filter_with_fallback,load_multi_column_filter |
| __all__ | __all__ | bioetl.infrastructure.adapters.openalex.__init__ | 1 |  |
| class | OpenAlexAdapter | bioetl.infrastructure.adapters.openalex.client | 677 | bases=BaseHttpAdapter; public=aclose,clear_request_collector,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,request_count |
| constant | OPENALEX_API_BASE | bioetl.infrastructure.adapters.openalex.client | 1 |  |
| function | _create_openalex_adapter | bioetl.infrastructure.adapters.openalex.client | 45 | (http_client: UnifiedHTTPClient | None, logger: LoggerPort | None, settings: Settings | None, **kwargs: Any) |
| class | TitleFallbackHandler | bioetl.infrastructure.adapters.openalex.fallback | 51 | bases=BaseTitleFallbackHandler |
| __all__ | __all__ | bioetl.infrastructure.adapters.pubchem.__init__ | 1 |  |
| class | PubChemAdapter | bioetl.infrastructure.adapters.pubchem.client | 288 | bases=FilterableStubMixin,BaseSyncAdapter; public=clear_request_collector,fetch,fetch_as_models,fetch_filtered,get_source_metadata,request_count |
| constant | PUBCHEM_DTO_MODELS | bioetl.infrastructure.adapters.pubchem.client | 1 |  |
| constant | PUBCHEM_API_BASE | bioetl.infrastructure.adapters.pubchem.constants | 1 |  |
| class | PubChemEntityMapper | bioetl.infrastructure.adapters.pubchem.entity_mapper | 137 | public=assay_to_dict,compound_to_dict,substance_to_dict |
| class | PubChemFetchStrategies | bioetl.infrastructure.adapters.pubchem.fetch_strategies | 308 | public=fetch_assays,fetch_by_cids,fetch_by_inchikey,fetch_by_query,fetch_by_smiles,fetch_substances |
| class | PubChemAssayRecord | bioetl.infrastructure.adapters.pubchem.models | 18 | bases=BaseModel |
| class | PubChemBioactivityRecord | bioetl.infrastructure.adapters.pubchem.models | 27 | bases=BaseModel |
| class | PubChemSubstanceRecord | bioetl.infrastructure.adapters.pubchem.models | 29 | bases=BaseModel |
| class | PubchemMoleculeApiRecord | bioetl.infrastructure.adapters.pubchem.models | 58 | bases=BaseModel |
| class | PubchemMoleculeDetailRecord | bioetl.infrastructure.adapters.pubchem.models | 64 | bases=BaseModel |
| constant | PUBCHEM_RECORD_MODELS | bioetl.infrastructure.adapters.pubchem.models | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.adapters.pubmed.__init__ | 1 |  |
| class | TitleFallbackHandler | bioetl.infrastructure.adapters.pubmed.fallback | 62 | bases=BaseTitleFallbackHandler |
| class | PubMedArticleId | bioetl.infrastructure.adapters.pubmed.models | 7 | bases=BaseModel |
| class | PubMedArticleRecord | bioetl.infrastructure.adapters.pubmed.models | 18 | bases=BaseModel |
| class | PubMedAuthor | bioetl.infrastructure.adapters.pubmed.models | 12 | bases=BaseModel |
| class | PubMedChemical | bioetl.infrastructure.adapters.pubmed.models | 8 | bases=BaseModel |
| class | PubMedExtendedRecord | bioetl.infrastructure.adapters.pubmed.models | 97 | bases=BaseModel |
| class | PubMedGrant | bioetl.infrastructure.adapters.pubmed.models | 9 | bases=BaseModel |
| class | PubMedJournal | bioetl.infrastructure.adapters.pubmed.models | 17 | bases=BaseModel |
| class | PubMedMeshHeading | bioetl.infrastructure.adapters.pubmed.models | 11 | bases=BaseModel |
| class | PubMedPubDate | bioetl.infrastructure.adapters.pubmed.models | 8 | bases=BaseModel |
| class | PubMedReference | bioetl.infrastructure.adapters.pubmed.models | 7 | bases=BaseModel |
| class | PubMedSearchResponse | bioetl.infrastructure.adapters.pubmed.models | 8 | bases=BaseModel |
| class | PubMedSearchResult | bioetl.infrastructure.adapters.pubmed.models | 23 | bases=BaseModel |
| constant | PUBMED_RECORD_MODELS | bioetl.infrastructure.adapters.pubmed.models | 1 |  |
| class | PubMedAdapter | bioetl.infrastructure.adapters.pubmed.pubmed_client | 542 | bases=NotSupportedMultiFilterMixin,BaseHttpAdapter; public=aclose,clear_request_collector,fetch,fetch_as_models,fetch_filtered,fetch_filtered_with_fallback,get_source_metadata,request_count |
| constant | ENTREZ_API_BASE | bioetl.infrastructure.adapters.pubmed.pubmed_client | 1 |  |
| constant | PUBMED_DTO_MODELS | bioetl.infrastructure.adapters.pubmed.pubmed_client | 1 |  |
| function | _create_pubmed_adapter | bioetl.infrastructure.adapters.pubmed.pubmed_client | 36 | (http_client: UnifiedHTTPClient | None, logger: LoggerPort | None, settings: Settings | None, **kwargs: Any) |
| class | PubMedXmlProcessor | bioetl.infrastructure.adapters.pubmed.xml_processor | 64 | public=extract_all_records,extract_record,find_articles,parse_response |
| __all__ | __all__ | bioetl.infrastructure.adapters.semanticscholar.__init__ | 1 |  |
| class | SemanticScholarAdapter | bioetl.infrastructure.adapters.semanticscholar.adapter | 536 | bases=BaseHttpAdapter; public=aclose,clear_request_collector,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,request_count |
| constant | DEFAULT_FIELDS | bioetl.infrastructure.adapters.semanticscholar.adapter | 1 |  |
| constant | SEMANTICSCHOLAR_BASE_URL | bioetl.infrastructure.adapters.semanticscholar.constants | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.adapters.semanticscholar.fallback | 1 |  |
| class | SemanticScholarTitleFallbackHandler | bioetl.infrastructure.adapters.semanticscholar.fallback | 168 | bases=BaseTitleFallbackHandler; public=titles_match |
| constant | DEFAULT_SEARCH_FIELDS | bioetl.infrastructure.adapters.semanticscholar.fallback | 1 |  |
| class | BaseSyncAdapter | bioetl.infrastructure.adapters.sync_base | 101 | bases=HealthCheckProviderMixin,DataSourcePort; public=aclose,close |
| __all__ | __all__ | bioetl.infrastructure.adapters.uniprot.__init__ | 1 |  |
| class | UniProtAdapter | bioetl.infrastructure.adapters.uniprot.client | 595 | bases=BaseHttpAdapter,PaginatedFetcherMixin; public=clear_request_collector,fetch,fetch_filtered,fetch_filtered_with_fallback,fetch_multi_filtered,get_source_metadata,request_count |
| constant | UNIPROT_BATCH_SIZE | bioetl.infrastructure.adapters.uniprot.client | 1 |  |
| class | FastaParser | bioetl.infrastructure.adapters.uniprot.fasta_parser | 82 | public=parse,parse_header |
| class | IDMappingJobError | bioetl.infrastructure.adapters.uniprot.idmapping_client | 12 | bases=Exception |
| class | IDMappingTimeoutError | bioetl.infrastructure.adapters.uniprot.idmapping_client | 15 | bases=Exception |
| class | UniProtIDMappingClient | bioetl.infrastructure.adapters.uniprot.idmapping_client | 586 | bases=BaseHttpAdapter; public=fetch,map_ids |
| class | UniProtComment | bioetl.infrastructure.adapters.uniprot.models | 31 | bases=BaseModel |
| class | UniProtCrossReference | bioetl.infrastructure.adapters.uniprot.models | 10 | bases=BaseModel |
| class | UniProtEcNumber | bioetl.infrastructure.adapters.uniprot.models | 6 | bases=BaseModel |
| class | UniProtEvidence | bioetl.infrastructure.adapters.uniprot.models | 8 | bases=BaseModel |
| class | UniProtExtraAttributes | bioetl.infrastructure.adapters.uniprot.models | 8 | bases=BaseModel |
| class | UniProtFeature | bioetl.infrastructure.adapters.uniprot.models | 16 | bases=BaseModel |
| class | UniProtFeatureLocation | bioetl.infrastructure.adapters.uniprot.models | 7 | bases=BaseModel |
| class | UniProtFeatureRecord | bioetl.infrastructure.adapters.uniprot.models | 11 | bases=BaseModel |
| class | UniProtFullName | bioetl.infrastructure.adapters.uniprot.models | 11 | bases=BaseModel |
| class | UniProtGene | bioetl.infrastructure.adapters.uniprot.models | 17 | bases=BaseModel |
| class | UniProtIsoform | bioetl.infrastructure.adapters.uniprot.models | 12 | bases=BaseModel |
| class | UniProtKeyword | bioetl.infrastructure.adapters.uniprot.models | 8 | bases=BaseModel |
| class | UniProtLocation | bioetl.infrastructure.adapters.uniprot.models | 9 | bases=BaseModel |
| class | UniProtName | bioetl.infrastructure.adapters.uniprot.models | 6 | bases=BaseModel |
| class | UniProtOrganism | bioetl.infrastructure.adapters.uniprot.models | 13 | bases=BaseModel |
| class | UniProtProteinDescription | bioetl.infrastructure.adapters.uniprot.models | 18 | bases=BaseModel |
| class | UniProtProteinRecord | bioetl.infrastructure.adapters.uniprot.models | 82 | bases=BaseModel |
| class | UniProtReaction | bioetl.infrastructure.adapters.uniprot.models | 12 | bases=BaseModel |
| class | UniProtRecommendedName | bioetl.infrastructure.adapters.uniprot.models | 14 | bases=BaseModel |
| class | UniProtSearchResponse | bioetl.infrastructure.adapters.uniprot.models | 8 | bases=BaseModel |
| class | UniProtSequence | bioetl.infrastructure.adapters.uniprot.models | 10 | bases=BaseModel |
| class | UniProtSequenceRecord | bioetl.infrastructure.adapters.uniprot.models | 12 | bases=BaseModel |
| class | UniProtSubcellularLocation | bioetl.infrastructure.adapters.uniprot.models | 8 | bases=BaseModel |
| class | UniProtText | bioetl.infrastructure.adapters.uniprot.models | 9 | bases=BaseModel |
| constant | UNIPROT_RECORD_MODELS | bioetl.infrastructure.adapters.uniprot.models | 1 |  |
| class | ValidationResult | bioetl.infrastructure.adapters.validation | 20 |  |
| constant | T | bioetl.infrastructure.adapters.validation | 1 |  |
| function | get_record_model | bioetl.infrastructure.adapters.validation | 47 | (provider: str, entity_type: str) |
| function | parse_with_validation | bioetl.infrastructure.adapters.validation | 43 | (record: dict[str, Any], model_class: type[T], strict: bool = False, logger: LoggerPort | None = None, context: str = '') |
| function | validate_record | bioetl.infrastructure.adapters.validation | 58 | (record: dict[str, Any], model_class: type[T], logger: LoggerPort | None = None, context: str = '') |
| function | validate_records | bioetl.infrastructure.adapters.validation | 28 | (records: list[dict[str, Any]], model_class: type[T], logger: LoggerPort | None = None, context: str = '') |
| __all__ | __all__ | bioetl.infrastructure.audit.__init__ | 1 |  |
| class | FileAuditAdapter | bioetl.infrastructure.audit.file_audit | 328 | public=aclose,get_entries,log_write |
| __all__ | __all__ | bioetl.infrastructure.checkpoint.__init__ | 1 |  |
| class | LocalCheckpoint | bioetl.infrastructure.checkpoint.local_checkpoint | 160 | public=aclose,delete,exists,list_all,load,save |
| __all__ | __all__ | bioetl.infrastructure.config.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.config._base | 1 |  |
| class | ObservabilitySettings | bioetl.infrastructure.config._base | 44 | bases=BaseSettings |
| class | PipelineSettings | bioetl.infrastructure.config._base | 16 | bases=BaseSettings |
| class | Settings | bioetl.infrastructure.config._base | 108 | bases=BaseSettings; public=bronze_path,checkpoint_path,gold_path,quarantine_path,settings_customise_sources,silver_path |
| class | YamlSettingsSource | bioetl.infrastructure.config._base | 40 | bases=PydanticBaseSettingsSource; public=get_field_value,prepare_field_value |
| function | _build_gold_filters | bioetl.infrastructure.config._base | 6 | (yaml_config: PipelineYamlConfig) |
| function | _build_silver_filters | bioetl.infrastructure.config._base | 7 | (yaml_config: PipelineYamlConfig) |
| function | _extract_source_fields | bioetl.infrastructure.config._base | 6 | (yaml_config: PipelineYamlConfig) |
| function | _extract_write_modes | bioetl.infrastructure.config._base | 20 | (yaml_config: PipelineYamlConfig) |
| function | get_pipeline_config | bioetl.infrastructure.config._base | 29 | (pipeline_name: str) |
| function | get_settings | bioetl.infrastructure.config._base | 3 | () |
| function | yaml_config_to_domain | bioetl.infrastructure.config._base | 74 | (yaml_config: PipelineYamlConfig, resolved_dq_config: DQConfig | None = None) |
| __all__ | __all__ | bioetl.infrastructure.config.base_config_loader | 1 |  |
| class | BaseConfigLoader | bioetl.infrastructure.config.base_config_loader | 129 | bases=ABC,Generic[T]; public=clear_cache,load |
| constant | T | bioetl.infrastructure.config.base_config_loader | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.config.dq_config_loader | 1 |  |
| class | DQConfigLoader | bioetl.infrastructure.config.dq_config_loader | 242 | public=clear_cache,load |
| __all__ | __all__ | bioetl.infrastructure.config.field_group_loader | 1 |  |
| class | FieldGroupLoadError | bioetl.infrastructure.config.field_group_loader | 2 | bases=ValueError |
| function | _parse_config | bioetl.infrastructure.config.field_group_loader | 37 | (raw: dict[str, Any], source: str) |
| function | _parse_field | bioetl.infrastructure.config.field_group_loader | 26 | (raw_field: dict[str, Any], group_id: FieldGroupId) |
| function | _parse_group | bioetl.infrastructure.config.field_group_loader | 40 | (raw_group: dict[str, Any], index: int) |
| function | load_field_groups | bioetl.infrastructure.config.field_group_loader | 28 | (path: Path) |
| __all__ | __all__ | bioetl.infrastructure.config.filter_config_loader | 1 |  |
| class | FilterConfigLoader | bioetl.infrastructure.config.filter_config_loader | 137 | bases=BaseConfigLoader[tuple[InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams]]; public=load |
| __all__ | __all__ | bioetl.infrastructure.config.pipeline_config_loader | 1 |  |
| class | ConfigLoader | bioetl.infrastructure.config.pipeline_config_loader | 265 | public=clear_cache,load_pipeline_config,resolve_dq_config |
| function | _apply_convention_defaults | bioetl.infrastructure.config_loader | 31 | (config: dict[str, Any]) |
| function | _apply_file_reference_defaults | bioetl.infrastructure.config_loader | 18 | (config: dict[str, Any], provider: str, entity_type: str) |
| function | _apply_layer_defaults | bioetl.infrastructure.config_loader | 26 | (layer: dict[str, Any], provider: str, entity_type: str, layer_name: str, primary_keys: list[str]) |
| function | _deep_merge | bioetl.infrastructure.config_loader | 11 | (base: dict[str, Any], override: dict[str, Any]) |
| function | _load_base_config | bioetl.infrastructure.config_loader | 14 | (config_path: Path) |
| function | _load_column_groups_config | bioetl.infrastructure.config_loader | 20 | (config_path: Path, column_groups_file: str) |
| function | _load_column_groups_section | bioetl.infrastructure.config_loader | 27 | (config: dict[str, Any], entity_config: dict[str, Any], config_path: Path) |
| function | _load_data_schema_config | bioetl.infrastructure.config_loader | 37 | (config_path: Path, data_schema_file: str) |
| function | _load_filter_config | bioetl.infrastructure.config_loader | 18 | (config_path: Path, filter_config_file: str) |
| function | _load_source_section | bioetl.infrastructure.config_loader | 10 | (config: dict[str, Any], config_path: Path) |
| function | _merge_filter_config | bioetl.infrastructure.config_loader | 57 | (config: dict[str, Any], filter_config: dict[str, Any], explicit_entity_config: dict[str, Any]) |
| function | load_pipeline_config | bioetl.infrastructure.config_loader | 57 | (pipeline_name: str) |
| function | load_source_config | bioetl.infrastructure.config_loader | 15 | (provider: str) |
| __all__ | __all__ | bioetl.infrastructure.export.__init__ | 1 |  |
| class | CsvExporter | bioetl.infrastructure.export.csv_exporter | 298 | public=clear,export |
| __all__ | __all__ | bioetl.infrastructure.export.dq_report_writer | 1 |  |
| class | DQReportWriter | bioetl.infrastructure.export.dq_report_writer | 289 | public=write_bronze_report,write_gold_report,write_silver_report |
| __all__ | __all__ | bioetl.infrastructure.locking.__init__ | 1 |  |
| class | MemoryLock | bioetl.infrastructure.locking.memory_lock | 247 | bases=LockPort; public=aclose,acquire,heartbeat,release,validate_owner |
| __all__ | __all__ | bioetl.infrastructure.observability.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.observability.anomaly.__init__ | 1 |  |
| class | AnomalyDetector | bioetl.infrastructure.observability.anomaly.detector | 161 | public=add_baseline_value,clear_baseline,detect,get_baseline_stats,set_threshold,update_baseline |
| __all__ | __all__ | bioetl.infrastructure.observability.anomaly.detectors.__init__ | 1 |  |
| class | DetectorStrategy | bioetl.infrastructure.observability.anomaly.detectors.base | 44 | bases=ABC; public=detect,get_severity |
| class | ZScoreDetector | bioetl.infrastructure.observability.anomaly.detectors.zscore | 86 | bases=DetectorStrategy; public=detect,get_severity |
| class | DataQualityMonitor | bioetl.infrastructure.observability.anomaly.monitor | 112 | public=add_metric,check_quality,get_baseline_stats,update_baseline_from_metrics |
| class | Anomaly | bioetl.infrastructure.observability.anomaly.types | 33 |  |
| class | AnomalySeverity | bioetl.infrastructure.observability.anomaly.types | 7 | bases=StrEnum |
| class | AnomalyType | bioetl.infrastructure.observability.anomaly.types | 7 | bases=StrEnum |
| class | StructlogLogger | bioetl.infrastructure.observability.logging | 84 | public=bind,debug,error,exception,info,warning |
| function | create_logger | bioetl.infrastructure.observability.logging | 51 | (pipeline: str, run_id: UUID, log_level: str = 'INFO', json_format: bool = True) |
| __all__ | __all__ | bioetl.infrastructure.observability.logging_config | 1 |  |
| function | _mask_secrets | bioetl.infrastructure.observability.logging_config | 17 | (value: Any) |
| function | configure_logging | bioetl.infrastructure.observability.logging_config | 65 | (json_format: bool = True, log_level: str = 'INFO', *, force: bool = False) |
| function | is_logging_configured | bioetl.infrastructure.observability.logging_config | 8 | () |
| function | reset_logging_config | bioetl.infrastructure.observability.logging_config | 10 | () |
| function | secret_filter_processor | bioetl.infrastructure.observability.logging_config | 29 | (logger: Any, _method_name: str, event_dict: dict[str, Any]) |
| class | MetricsCollector | bioetl.infrastructure.observability.metrics | 50 | public=record_error,record_processed |
| constant | ARCHIVE_DURATION_SECONDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | ARCHIVE_FILES_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | BATCH_SIZE_RECORDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | CIRCUIT_BREAKER_FAILURE_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | CIRCUIT_BREAKER_STATE | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | CIRCUIT_BREAKER_SUCCESS_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | CIRCUIT_BREAKER_TRIPS_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DATA_FRESHNESS_SECONDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_ANOMALY_DETECTED | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_BASELINE_SAMPLES | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_BASELINE_UPDATED | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_CHECK_DURATION_MS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_RECORDS_QUARANTINED_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | DQ_VALIDATION_SCORE | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | ERRORS_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | FILTER_IDS_DUPLICATES_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | FILTER_IDS_LOADED_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | HEALTH_CHECK_DURATION_SECONDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | INFRASTRUCTURE_VALIDATED | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | PIPELINE_DURATION_SECONDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | PIPELINE_HEALTH_CHECK_PASSED | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | RECORDS_PROCESSED_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | VACUUM_DURATION_SECONDS | bioetl.infrastructure.observability.metrics | 1 |  |
| constant | VACUUM_FILES_REMOVED_TOTAL | bioetl.infrastructure.observability.metrics | 1 |  |
| class | MetricsServerAdapter | bioetl.infrastructure.observability.metrics_server_adapter | 67 | public=is_running,reset,start |
| class | NoOpLogger | bioetl.infrastructure.observability.noop_logger | 36 | public=bind,debug,error,exception,info,warning |
| class | PrometheusMetrics | bioetl.infrastructure.observability.prometheus_metrics | 52 | bases=MetricsPort; public=close,increment_counter,observe_histogram,set_gauge |
| constant | COUNTERS | bioetl.infrastructure.observability.prometheus_metrics | 1 |  |
| constant | GAUGES | bioetl.infrastructure.observability.prometheus_metrics | 1 |  |
| constant | HISTOGRAMS | bioetl.infrastructure.observability.prometheus_metrics | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.observability.server | 1 |  |
| function | _handle_os_error | bioetl.infrastructure.observability.server | 13 | (port: int, e: OSError, retry_count: int, fail_fast: bool, logger: LoggerPort) |
| function | _handle_port_in_use | bioetl.infrastructure.observability.server | 19 | (port: int, e: OSError, fail_fast: bool, logger: LoggerPort) |
| function | _handle_unexpected_error | bioetl.infrastructure.observability.server | 14 | (port: int, e: Exception, fail_fast: bool, logger: LoggerPort) |
| function | reset_server_state | bioetl.infrastructure.observability.server | 5 | () |
| function | start_metrics_server | bioetl.infrastructure.observability.server | 61 | (port: int = 8000, *, fail_fast: bool = False, retry_count: int = 3, retry_delay: float = 1.0, logger: LoggerPort | None = None) |
| __all__ | __all__ | bioetl.infrastructure.observability.tracing | 1 |  |
| class | OpenTelemetryTracer | bioetl.infrastructure.observability.tracing | 57 | public=close,get_tracer |
| class | UnifiedLogger | bioetl.infrastructure.observability.unified_logger | 155 | public=bind,debug,error,exception,info,warning |
| function | create_unified_logger | bioetl.infrastructure.observability.unified_logger | 26 | (pipeline: str, run_id: str | UUID, log_level: str = 'INFO', json_format: bool = True) |
| __all__ | __all__ | bioetl.infrastructure.quarantine.__init__ | 1 |  |
| function | get_statistics | bioetl.infrastructure.quarantine.operations | 46 | (base_path: str, storage_options: dict[str, str] | None, pipeline: str) |
| function | inspect_records | bioetl.infrastructure.quarantine.operations | 34 | (base_path: str, storage_options: dict[str, str] | None, pipeline: str, limit: int = 100, error_code: str | None = None, dq_status: QuarantineRecordStatus | None = None) |
| function | purge_records | bioetl.infrastructure.quarantine.operations | 43 | (base_path: str, storage_options: dict[str, str] | None, pipeline: str, older_than_days: int = 30, *, now: datetime) |
| function | replay_records | bioetl.infrastructure.quarantine.operations | 45 | (base_path: str, storage_options: dict[str, str] | None, pipeline: str, error_code: str | None = None, max_age_days: int = 7, *, now: datetime) |
| constant | MAX_PAYLOAD_SIZE | bioetl.infrastructure.quarantine.record_encoding | 1 |  |
| function | calculate_hash | bioetl.infrastructure.quarantine.record_encoding | 11 | (payload_json: str) |
| function | quote_literal | bioetl.infrastructure.quarantine.record_encoding | 18 | (value: Any) |
| class | UnifiedQuarantine | bioetl.infrastructure.quarantine.unified | 173 | public=aclose,get_stats,inspect,purge,replay,update_status,write |
| __all__ | __all__ | bioetl.infrastructure.schemas.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.schemas.base_schemas | 1 |  |
| class | BaseApiConfig | bioetl.infrastructure.schemas.base_schemas | 43 | bases=BaseModel; public=to_domain |
| class | BaseCircuitBreakerConfig | bioetl.infrastructure.schemas.base_schemas | 35 | bases=BaseModel; public=to_domain |
| class | BaseClientConfig | bioetl.infrastructure.schemas.base_schemas | 9 | bases=BaseModel |
| class | BaseCsvExportConfig | bioetl.infrastructure.schemas.base_schemas | 35 | bases=BaseModel |
| class | BaseDQConfig | bioetl.infrastructure.schemas.base_schemas | 26 | bases=BaseDQThresholds; public=to_domain |
| class | BaseDQThresholds | bioetl.infrastructure.schemas.base_schemas | 26 | bases=BaseModel; public=validate_thresholds |
| class | BaseFilterColumnSchema | bioetl.infrastructure.schemas.base_schemas | 14 | bases=BaseModel |
| class | BaseGoldColumnFilterConfig | bioetl.infrastructure.schemas.base_schemas | 40 | bases=BaseModel; public=validate_operator_values |
| class | BaseGoldFiltersConfig | bioetl.infrastructure.schemas.base_schemas | 107 | bases=BaseModel; public=to_domain |
| class | BaseGoldListContainsFilterConfig | bioetl.infrastructure.schemas.base_schemas | 17 | bases=BaseModel |
| class | BaseGoldListLengthFilterConfig | bioetl.infrastructure.schemas.base_schemas | 18 | bases=BaseModel |
| class | BaseGoldRangeFilterConfig | bioetl.infrastructure.schemas.base_schemas | 28 | bases=BaseModel |
| class | BaseInputFilterConfig | bioetl.infrastructure.schemas.base_schemas | 108 | bases=BaseModel; public=to_domain,validate_column_config |
| class | BaseMaintenanceConfig | bioetl.infrastructure.schemas.base_schemas | 22 | bases=BaseModel |
| class | BaseRateLimitConfig | bioetl.infrastructure.schemas.base_schemas | 24 | bases=BaseModel |
| __all__ | __all__ | bioetl.infrastructure.schemas.composite_config | 1 |  |
| class | AggregationFieldSchema | bioetl.infrastructure.schemas.composite_config | 32 | bases=BaseModel; public=to_domain |
| class | AggregationSchema | bioetl.infrastructure.schemas.composite_config | 19 | bases=BaseModel; public=to_domain |
| class | ColumnGroupSchema | bioetl.infrastructure.schemas.composite_config | 32 | bases=BaseModel; public=validate_fields_or_pattern |
| class | CompositeConfigFileSchema | bioetl.infrastructure.schemas.composite_config | 23 | bases=BaseModel; public=to_domain |
| class | CompositeConfigSchema | bioetl.infrastructure.schemas.composite_config | 108 | bases=BaseModel; public=to_domain,validate_dependency_join_keys,validate_enricher_join_keys,validate_has_enrichers_or_dependencies,validate_unique_dependency_names,validate_unique_enricher_names |
| class | CompositeDQSchema | bioetl.infrastructure.schemas.composite_config | 38 | bases=BaseModel; public=to_domain,validate_threshold_order |
| class | DQOverrideSchema | bioetl.infrastructure.schemas.composite_config | 29 | bases=BaseModel; public=to_domain,validate_threshold_order |
| class | DependencySchema | bioetl.infrastructure.schemas.composite_config | 95 | bases=BaseModel; public=to_domain,validate_filter_fields_exclusive,validate_join_keys_not_empty |
| class | EnricherSchema | bioetl.infrastructure.schemas.composite_config | 71 | bases=BaseModel; public=to_domain,validate_aggregation_required,validate_join_keys_not_empty |
| class | ExecutionSchema | bioetl.infrastructure.schemas.composite_config | 21 | bases=BaseModel; public=to_domain |
| class | LineageSchema | bioetl.infrastructure.schemas.composite_config | 20 | bases=BaseModel; public=to_domain |
| class | MergeOutputSchema | bioetl.infrastructure.schemas.composite_config | 5 | bases=BaseModel |
| class | MergeSchema | bioetl.infrastructure.schemas.composite_config | 76 | bases=BaseModel; public=to_domain,validate_explicit_rules_requires_priorities |
| class | RetrySchema | bioetl.infrastructure.schemas.composite_config | 9 | bases=BaseModel |
| class | SeedSchema | bioetl.infrastructure.schemas.composite_config | 33 | bases=BaseModel; public=to_domain,validate_output_keys_not_empty |
| __all__ | __all__ | bioetl.infrastructure.schemas.dq_config | 1 |  |
| class | DQConfigFile | bioetl.infrastructure.schemas.dq_config | 203 | bases=BaseModel; public=to_domain |
| class | ThresholdsConfig | bioetl.infrastructure.schemas.dq_config | 45 | bases=BaseModel; public=validate_order |
| __all__ | __all__ | bioetl.infrastructure.schemas.dq_report_config | 1 |  |
| class | BronzeDQReportConfig | bioetl.infrastructure.schemas.dq_report_config | 45 | bases=BaseModel; public=get_checks_enums,get_format_enum |
| class | BronzeSinkConfig | bioetl.infrastructure.schemas.dq_report_config | 10 | bases=BaseModel |
| class | GoldDQReportConfig | bioetl.infrastructure.schemas.dq_report_config | 48 | bases=BaseModel; public=get_checks_enums,get_format_enum |
| class | GoldSinkConfig | bioetl.infrastructure.schemas.dq_report_config | 10 | bases=BaseModel |
| class | SilverDQReportConfig | bioetl.infrastructure.schemas.dq_report_config | 49 | bases=BaseModel; public=get_checks_enums,get_format_enum |
| class | SilverSinkConfig | bioetl.infrastructure.schemas.dq_report_config | 24 | bases=BaseModel |
| __all__ | __all__ | bioetl.infrastructure.schemas.filter_config | 1 |  |
| class | FilterConfigFile | bioetl.infrastructure.schemas.filter_config | 81 | bases=BaseModel; public=to_domain,validate_extraction_params |
| class | GoldFiltersFileConfig | bioetl.infrastructure.schemas.filter_config | 26 | bases=BaseGoldFiltersConfig; public=to_domain |
| class | InputFilterFileConfig | bioetl.infrastructure.schemas.filter_config | 25 | bases=BaseInputFilterConfig; public=to_domain |
| class | SilverFiltersFileConfig | bioetl.infrastructure.schemas.filter_config | 22 | bases=BaseGoldFiltersConfig; public=to_domain |
| class | ApiConfig | bioetl.infrastructure.schemas.pipeline_config | 23 | bases=BaseModel; public=to_domain |
| class | CircuitBreakerConfig | bioetl.infrastructure.schemas.pipeline_config | 19 | bases=BaseModel; public=to_domain |
| class | ClientSourceConfig | bioetl.infrastructure.schemas.pipeline_config | 5 | bases=BaseModel |
| class | ConditionalValidationConfig | bioetl.infrastructure.schemas.pipeline_config | 12 | bases=BaseModel |
| class | CrossFieldValidationConfig | bioetl.infrastructure.schemas.pipeline_config | 20 | bases=BaseModel |
| class | CsvExportConfig | bioetl.infrastructure.schemas.pipeline_config | 8 | bases=BaseModel |
| class | DQConfig | bioetl.infrastructure.schemas.pipeline_config | 144 | bases=BaseModel; public=to_domain,validate_thresholds |
| class | DQReportConfig | bioetl.infrastructure.schemas.pipeline_config | 14 | bases=BaseModel |
| class | FieldValidationConfig | bioetl.infrastructure.schemas.pipeline_config | 27 | bases=BaseModel |
| class | FilterColumnSchema | bioetl.infrastructure.schemas.pipeline_config | 2 | bases=BaseFilterColumnSchema |
| class | GoldColumnFilterConfig | bioetl.infrastructure.schemas.pipeline_config | 13 | bases=BaseGoldColumnFilterConfig |
| class | GoldFiltersConfig | bioetl.infrastructure.schemas.pipeline_config | 23 | bases=BaseGoldFiltersConfig |
| class | GoldListContainsFilterConfig | bioetl.infrastructure.schemas.pipeline_config | 2 | bases=BaseGoldListContainsFilterConfig |
| class | GoldListLengthFilterConfig | bioetl.infrastructure.schemas.pipeline_config | 2 | bases=BaseGoldListLengthFilterConfig |
| class | GoldRangeFilterConfig | bioetl.infrastructure.schemas.pipeline_config | 2 | bases=BaseGoldRangeFilterConfig |
| class | InputFilterConfig | bioetl.infrastructure.schemas.pipeline_config | 11 | bases=BaseInputFilterConfig |
| class | MaintenanceConfig | bioetl.infrastructure.schemas.pipeline_config | 20 | bases=BaseModel |
| class | PipelineYamlConfig | bioetl.infrastructure.schemas.pipeline_config | 187 | bases=BaseModel; public=to_domain,validate_batch_size,validate_entity_type_canonical,validate_medallion_formats,validate_provider |
| class | ProviderSourceConfig | bioetl.infrastructure.schemas.pipeline_config | 14 | bases=BaseModel |
| class | RateLimitSourceConfig | bioetl.infrastructure.schemas.pipeline_config | 8 | bases=BaseModel |
| class | SinkDQReportConfig | bioetl.infrastructure.schemas.pipeline_config | 15 | bases=BaseModel |
| class | SinkLayerConfig | bioetl.infrastructure.schemas.pipeline_config | 41 | bases=BaseModel |
| class | SinkLineageConfig | bioetl.infrastructure.schemas.pipeline_config | 28 | bases=BaseModel |
| class | SinkMetadataConfig | bioetl.infrastructure.schemas.pipeline_config | 79 | bases=BaseModel; public=to_domain |
| class | SortByConfig | bioetl.infrastructure.schemas.pipeline_config | 11 | bases=BaseModel |
| class | SourceConfig | bioetl.infrastructure.schemas.pipeline_config | 22 | bases=BaseModel |
| class | TransformConfig | bioetl.infrastructure.schemas.pipeline_config | 40 | bases=BaseModel; public=validate_semver |
| constant | SEMVER_PATTERN | bioetl.infrastructure.schemas.pipeline_config | 1 |  |
| constant | CHEMBL_ACTIVITY_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_ASSAY_PARAMETERS_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_ASSAY_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_CELL_LINE_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_COMPOUND_RECORD_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_DOCUMENT_SIMILARITY_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_DOCUMENT_TERM_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_MOLECULE_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_PROTEIN_CLASS_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_PUBLICATION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_SUBCELLULAR_FRACTION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_TARGET_COMPONENT_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_TARGET_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CHEMBL_TISSUE_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | CROSSREF_PUBLICATION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | OPENALEX_PUBLICATION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | PUBCHEM_COMPOUND_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | PUBMED_PUBLICATION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | SEMANTICSCHOLAR_PUBLICATION_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | UNIPROT_ID_MAPPING_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| constant | UNIPROT_PROTEIN_SCHEMA | bioetl.infrastructure.schemas.silver | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.schemas.source_config | 1 |  |
| class | CircuitBreakerYamlConfig | bioetl.infrastructure.schemas.source_config | 17 | bases=BaseCircuitBreakerConfig; public=to_domain |
| class | ProviderConfigYaml | bioetl.infrastructure.schemas.source_config | 23 | bases=BaseModel |
| class | SourceSectionConfig | bioetl.infrastructure.schemas.source_config | 28 | bases=BaseModel |
| class | SourceYamlConfig | bioetl.infrastructure.schemas.source_config | 122 | bases=BaseModel; public=base_url,batch_size,circuit_breaker,max_retries,max_url_length,page_size,provider,provider_config,rate_limit,retry_base_delay,retry_max_delay,timeout_sec,to_adapter_config |
| __all__ | __all__ | bioetl.infrastructure.security.__init__ | 1 |  |
| class | SaltConfig | bioetl.infrastructure.security.pii_hasher | 43 | public=from_env |
| class | Sha256PiiHasher | bioetl.infrastructure.security.pii_hasher | 127 | public=from_env,get_salt_id,hash_list,hash_value |
| __all__ | __all__ | bioetl.infrastructure.serialization.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.serialization.encoders | 1 |  |
| class | OrjsonEncoder | bioetl.infrastructure.serialization.encoders | 87 | public=dumps,dumps_canonical,loads |
| class | StdLibJsonEncoder | bioetl.infrastructure.serialization.encoders | 66 | public=dumps,dumps_canonical,loads |
| function | get_json_encoder | bioetl.infrastructure.serialization.encoders | 39 | () |
| function | reset_encoder_cache | bioetl.infrastructure.serialization.encoders | 7 | () |
| __all__ | __all__ | bioetl.infrastructure.storage.__init__ | 1 |  |
| class | AtomicWriteError | bioetl.infrastructure.storage._atomic | 7 | bases=Exception |
| class | AtomicWriteGroup | bioetl.infrastructure.storage._atomic | 114 | public=add,commit,rollback |
| function | atomic_write | bioetl.infrastructure.storage._atomic | 62 | (target: Path, mode: str = 'wb', suffix: str = '.tmp', prefix: str = '.', encoding: str | None = None) |
| function | atomic_write_bytes | bioetl.infrastructure.storage._atomic | 13 | (target: Path, data: bytes) |
| function | atomic_write_text | bioetl.infrastructure.storage._atomic | 14 | (target: Path, text: str, encoding: str = 'utf-8') |
| __all__ | __all__ | bioetl.infrastructure.storage.arrow_converter | 1 |  |
| class | ArrowDataConverter | bioetl.infrastructure.storage.arrow_converter | 161 | public=convert_records_to_arrow,sanitize_type_for_delta |
| class | BaseDeltaWriter | bioetl.infrastructure.storage.base_delta_writer | 249 | public=clear,get_table_path,read_table |
| function | _get_string_fields | bioetl.infrastructure.storage.base_delta_writer | 26 | (schema: pa.Schema) |
| function | _serialize_value | bioetl.infrastructure.storage.base_delta_writer | 27 | (value: Any, is_string_field: bool) |
| function | coerce_null_types_for_delta | bioetl.infrastructure.storage.base_delta_writer | 42 | (table: pa.Table) |
| class | BronzeWriter | bioetl.infrastructure.storage.bronze_writer | 767 | public=cleanup_old_files,list_batches,read_bronze,write_bronze |
| class | DeltaReader | bioetl.infrastructure.storage.delta_reader | 172 | public=aclose,get_row_count,get_schema,read_table,table_exists |
| __all__ | __all__ | bioetl.infrastructure.storage.gold_writer | 1 |  |
| class | GoldWriter | bioetl.infrastructure.storage.gold_writer | 894 | bases=BaseDeltaWriter; public=get_history,read_gold,write_gold,write_gold_merged |
| constant | T | bioetl.infrastructure.storage.gold_writer | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.storage.metadata_builder | 1 |  |
| class | GoldMetadataBuilder | bioetl.infrastructure.storage.metadata_builder | 228 | public=build_fallback_metadata,build_merged_metadata |
| class | SilverMetadataBuilder | bioetl.infrastructure.storage.metadata_builder | 134 | public=build_merged_metadata |
| function | _extract_schema_metadata | bioetl.infrastructure.storage.metadata_builder | 79 | (gold_schema: Any | None) |
| function | _get_bioetl_version | bioetl.infrastructure.storage.metadata_builder | 10 | () |
| function | _get_git_commit_cached | bioetl.infrastructure.storage.metadata_builder | 25 | () |
| function | _parse_table_name | bioetl.infrastructure.storage.metadata_builder | 25 | (table_name: str) |
| class | MetadataWriter | bioetl.infrastructure.storage.metadata_writer | 189 | public=aclose,write_bronze_metadata,write_gold_metadata,write_silver_metadata |
| constant | METADATA_FILENAME | bioetl.infrastructure.storage.metadata_writer | 1 |  |
| function | _get_metadata_filename | bioetl.infrastructure.storage.metadata_writer | 14 | (provider: str | None, entity: str | None) |
| class | RetentionManager | bioetl.infrastructure.storage.retention_manager | 185 | public=get_table_info,optimize,time_travel,vacuum |
| __all__ | __all__ | bioetl.infrastructure.storage.silver_writer | 1 |  |
| class | SilverWriter | bioetl.infrastructure.storage.silver_writer | 1075 | bases=BaseDeltaWriter; public=get_table_info,optimize,read_silver,time_travel,vacuum,write_silver,write_silver_merged |
| __all__ | __all__ | bioetl.infrastructure.system.__init__ | 1 |  |
| __all__ | __all__ | bioetl.infrastructure.system.memory_monitor | 1 |  |
| class | MemoryMonitor | bioetl.infrastructure.system.memory_monitor | 254 | public=calculate_max_batch_size,estimate_batch_memory_mb,get_memory_stats,get_recommended_batch_size,is_under_pressure |
| function | _check_psutil_available | bioetl.infrastructure.system.memory_monitor | 12 | () |
| __all__ | __all__ | bioetl.infrastructure.validation.__init__ | 1 |  |
| class | BasePanderaValidator | bioetl.infrastructure.validation.pandera_validator | 89 | public=validate |
| class | NoOpValidator | bioetl.infrastructure.validation.pandera_validator | 19 | public=validate |
| class | PanderaGoldValidator | bioetl.infrastructure.validation.pandera_validator | 60 | bases=BasePanderaValidator |
| class | PanderaSilverValidator | bioetl.infrastructure.validation.pandera_validator | 17 | bases=BasePanderaValidator |

### 1.4 Composition Layer
| Type | Name | Module | LOC | Details |
|------|------|--------|-----|---------|
| class | ArchiveOptions | bioetl.composition._pipeline_execution | 10 |  |
| class | VacuumOptions | bioetl.composition._pipeline_execution | 10 |  |
| function | _ensure_registrations | bioetl.composition._pipeline_execution | 7 | () |
| function | build_pipeline_context | bioetl.composition._pipeline_execution | 74 | (name: str, options: RunOptions) |
| function | create_pipeline_runner | bioetl.composition._pipeline_execution | 27 | (name: str, options: RunOptions) |
| function | ensure_metrics_server_started | bioetl.composition._pipeline_execution | 16 | () |
| function | run_pipeline | bioetl.composition._pipeline_execution | 74 | (name: str, options: RunOptions) |
| function | archive_table | bioetl.composition._resource_management | 21 | (table: str, options: ArchiveOptions) |
| function | get_checkpoint_manager | bioetl.composition._resource_management | 17 | (pipeline: str) |
| function | get_lifecycle_service | bioetl.composition._resource_management | 14 | () |
| function | get_quarantine_manager | bioetl.composition._resource_management | 17 | (pipeline: str) |
| function | inspect_quarantine | bioetl.composition._resource_management | 20 | (pipeline: str, limit: int = 100) |
| function | list_checkpoints | bioetl.composition._resource_management | 19 | (pipeline: str) |
| function | preview_cleanup | bioetl.composition._resource_management | 23 | (pipeline: str) |
| function | vacuum_table | bioetl.composition._resource_management | 21 | (table: str, options: VacuumOptions) |
| function | cleanup_bronze | bioetl.composition._services | 26 | (retention_days: int = 90, dry_run: bool = False) |
| function | get_bronze_cleanup_service | bioetl.composition._services | 16 | () |
| function | get_checkpoint_service | bioetl.composition._services | 17 | () |
| function | get_config_service | bioetl.composition._services | 18 | () |
| function | get_export_service | bioetl.composition._services | 17 | () |
| function | get_health_server_dependencies | bioetl.composition._services | 8 | () |
| function | get_health_service | bioetl.composition._services | 21 | () |
| function | get_lock_service | bioetl.composition._services | 19 | () |
| function | get_metrics_service | bioetl.composition._services | 19 | () |
| function | get_pipeline_runner_service | bioetl.composition._services | 20 | () |
| function | get_quarantine_service | bioetl.composition._services | 17 | () |
| function | get_quarantine_store | bioetl.composition._services | 19 | (pipeline: str) |
| function | get_vacuum_service | bioetl.composition._services | 17 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.__init__ | 1 |  |
| __all__ | __all__ | bioetl.composition.bootstrap.assembly.__init__ | 1 |  |
| __all__ | __all__ | bioetl.composition.bootstrap.assembly.checkpoint | 1 |  |
| function | bootstrap_checkpoint | bioetl.composition.bootstrap.assembly.checkpoint | 14 | (pipeline_name: str) |
| function | bootstrap_checkpoint_port | bioetl.composition.bootstrap.assembly.checkpoint | 19 | (pipeline_name: str) |
| function | bootstrap_quarantine | bioetl.composition.bootstrap.assembly.checkpoint | 11 | () |
| function | bootstrap_quarantine_port | bioetl.composition.bootstrap.assembly.checkpoint | 14 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.assembly.storage | 1 |  |
| function | bootstrap_storage | bioetl.composition.bootstrap.assembly.storage | 15 | (*, enable_csv_export: bool = False) |
| function | bootstrap_storage_adapter | bioetl.composition.bootstrap.assembly.storage | 82 | (*, enable_csv_export: bool = False) |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.__init__ | 1 |  |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.checkpoint | 1 |  |
| function | bootstrap_checkpoint_manager | bioetl.composition.bootstrap.cli.checkpoint | 24 | (pipeline_name: str) |
| function | bootstrap_checkpoint_service | bioetl.composition.bootstrap.cli.checkpoint | 21 | () |
| function | bootstrap_quarantine_manager | bioetl.composition.bootstrap.cli.checkpoint | 17 | (pipeline_name: str) |
| function | bootstrap_quarantine_service | bioetl.composition.bootstrap.cli.checkpoint | 15 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.config | 1 |  |
| function | bootstrap_config_service | bioetl.composition.bootstrap.cli.config | 26 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.health | 1 |  |
| class | HealthServerDependencies | bioetl.composition.bootstrap.cli.health | 13 |  |
| function | bootstrap_health_server_dependencies | bioetl.composition.bootstrap.cli.health | 28 | () |
| function | bootstrap_health_service | bioetl.composition.bootstrap.cli.health | 21 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.lock | 1 |  |
| function | bootstrap_lock_service | bioetl.composition.bootstrap.cli.lock | 17 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.metrics | 1 |  |
| function | bootstrap_metrics_service | bioetl.composition.bootstrap.cli.metrics | 21 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.noop | 1 |  |
| function | create_noop_logger | bioetl.composition.bootstrap.cli.noop | 14 | () |
| function | create_noop_metrics | bioetl.composition.bootstrap.cli.noop | 14 | () |
| function | create_noop_observability_bundle | bioetl.composition.bootstrap.cli.noop | 20 | () |
| function | create_noop_tracing | bioetl.composition.bootstrap.cli.noop | 16 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.cli.storage | 1 |  |
| function | _create_table_collector | bioetl.composition.bootstrap.cli.storage | 48 | () |
| function | bootstrap_bronze_cleanup_service | bioetl.composition.bootstrap.cli.storage | 13 | () |
| function | bootstrap_cleanup | bioetl.composition.bootstrap.cli.storage | 11 | () |
| function | bootstrap_cleanup_service | bioetl.composition.bootstrap.cli.storage | 15 | () |
| function | bootstrap_export_service | bioetl.composition.bootstrap.cli.storage | 31 | () |
| function | bootstrap_lifecycle_service | bioetl.composition.bootstrap.cli.storage | 13 | () |
| function | bootstrap_vacuum_service | bioetl.composition.bootstrap.cli.storage | 20 | () |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.__init__ | 1 |  |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.assembly | 1 |  |
| class | VacuumSettings | bioetl.composition.bootstrap.runtime.assembly | 13 |  |
| function | assemble_cached_bronze_context | bioetl.composition.bootstrap.runtime.assembly | 40 | (ctx: PipelineRunContext) |
| function | assemble_filter_config | bioetl.composition.bootstrap.runtime.assembly | 50 | (*, yaml_filter: YamlInputFilter, ctx: PipelineRunContext, test_mode: bool) |
| function | assemble_runtime_config | bioetl.composition.bootstrap.runtime.assembly | 56 | (*, run_type: RunType, resume: bool, limit: int | None, query: str | None, dry_run: bool, heartbeat_interval: int, vacuum: VacuumSettings, skip_gold: bool = False) |
| function | assemble_vacuum_settings | bioetl.composition.bootstrap.runtime.assembly | 52 | (*, cli_vacuum: VacuumConfig, yaml_maintenance: MaintenanceConfig) |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.composite | 1 |  |
| constant | COMPOSITE_CONFIG_DIR | bioetl.composition.bootstrap.runtime.composite | 1 |  |
| constant | FIELD_GROUP_CONFIG_DIR | bioetl.composition.bootstrap.runtime.composite | 1 |  |
| function | _build_fallback_mapping | bioetl.composition.bootstrap.runtime.composite | 15 | (keys: pl.DataFrame, filter_key: str, join_keys: tuple[str, ...]) |
| function | _create_dq_report_service | bioetl.composition.bootstrap.runtime.composite | 30 | (logger: LoggerPort, settings: Settings) |
| function | _extract_field_values | bioetl.composition.bootstrap.runtime.composite | 15 | (keys: pl.DataFrame, field: str) |
| function | _extract_filter_ids_from_keys | bioetl.composition.bootstrap.runtime.composite | 29 | (enricher_cfg: EnricherConfig, keys: pl.DataFrame, logger: LoggerPort | None = None) |
| function | _extract_multi_filter_ids | bioetl.composition.bootstrap.runtime.composite | 44 | (dep_cfg: DependencyConfig, keys: pl.DataFrame, logger: LoggerPort | None = None) |
| function | _find_filter_key | bioetl.composition.bootstrap.runtime.composite | 11 | (join_keys: tuple[str, ...], columns: list[str]) |
| function | _load_field_group_registry | bioetl.composition.bootstrap.runtime.composite | 48 | (composite_name: str, logger: LoggerPort) |
| function | _resolve_bronze_opts | bioetl.composition.bootstrap.runtime.composite | 25 | (runtime: CompositeRuntimeConfig, phase_override: bool | None) |
| function | bootstrap_composite_pipeline | bioetl.composition.bootstrap.runtime.composite | 20 | (config: CompositeConfig, runtime: CompositeRuntimeConfig, run_id: str | None = None) |
| function | bootstrap_composite_runner | bioetl.composition.bootstrap.runtime.composite | 260 | (config: CompositeConfig, runtime: CompositeRuntimeConfig, run_id: str | None = None) |
| function | load_composite_config | bioetl.composition.bootstrap.runtime.composite | 44 | (name: str) |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.observability | 1 |  |
| function | bootstrap_dq_monitor | bioetl.composition.bootstrap.runtime.observability | 17 | (settings: Settings, logger: LoggerPort | None = None) |
| function | bootstrap_dq_monitor_port | bioetl.composition.bootstrap.runtime.observability | 46 | (settings: Settings, logger: LoggerPort | None = None) |
| function | bootstrap_logger | bioetl.composition.bootstrap.runtime.observability | 20 | (pipeline: str, run_id: UUID | None = None, log_level: str = 'INFO') |
| function | bootstrap_logger_port | bioetl.composition.bootstrap.runtime.observability | 28 | (pipeline: str, run_id: UUID | None = None, log_level: str = 'INFO') |
| function | bootstrap_metrics | bioetl.composition.bootstrap.runtime.observability | 17 | (settings: Settings) |
| function | bootstrap_metrics_port | bioetl.composition.bootstrap.runtime.observability | 25 | (settings: Settings) |
| function | bootstrap_observability | bioetl.composition.bootstrap.runtime.observability | 27 | (pipeline: str, run_id: UUID, settings: Settings, log_level: str = 'INFO') |
| function | bootstrap_observability_bundle | bioetl.composition.bootstrap.runtime.observability | 67 | (pipeline: str, run_id: UUID, settings: Settings, log_level: str = 'INFO') |
| function | bootstrap_tracer | bioetl.composition.bootstrap.runtime.observability | 18 | (settings: Settings, service_name: str = 'bioetl') |
| function | bootstrap_tracer_port | bioetl.composition.bootstrap.runtime.observability | 24 | (settings: Settings, service_name: str = 'bioetl') |
| function | maybe_start_metrics_server | bioetl.composition.bootstrap.runtime.observability | 32 | (settings: Settings) |
| function | validate_observability_preflight | bioetl.composition.bootstrap.runtime.observability | 43 | (tracer: TracingPort, metrics: MetricsPort, environment: str, logger: LoggerPort) |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.pipeline | 1 |  |
| function | bootstrap_pipeline | bioetl.composition.bootstrap.runtime.pipeline | 18 | (ctx: PipelineRunContext, registry: PipelineRegistry | None = None) |
| function | bootstrap_pipeline_runner | bioetl.composition.bootstrap.runtime.pipeline | 120 | (ctx: PipelineRunContext, registry: PipelineRegistry | None = None) |
| __all__ | __all__ | bioetl.composition.bootstrap.runtime.runner | 1 |  |
| function | bootstrap_pipeline_runner_service | bioetl.composition.bootstrap.runtime.runner | 36 | (registry: PipelineRegistry | None = None) |
| __all__ | __all__ | bioetl.composition.bootstrap_contexts | 1 |  |
| class | DQConfigsContext | bioetl.composition.bootstrap_contexts | 15 |  |
| class | DQOutputPathsContext | bioetl.composition.bootstrap_contexts | 17 |  |
| class | PipelineCallbacksContext | bioetl.composition.bootstrap_contexts | 23 |  |
| class | RateLimitConfig | bioetl.composition.bootstrap_contexts | 12 |  |
| __all__ | __all__ | bioetl.composition.bootstrap_logger | 1 |  |
| class | BootstrapLogger | bioetl.composition.bootstrap_logger | 53 | public=debug,error,info,warning |
| function | get_bootstrap_logger | bioetl.composition.bootstrap_logger | 35 | () |
| function | reset_bootstrap_logger | bioetl.composition.bootstrap_logger | 8 | () |
| class | FilterConfigBuilder | bioetl.composition.builders | 178 | public=build,from_direct_ids,from_direct_multi_ids |
| __all__ | __all__ | bioetl.composition.entrypoints | 1 |  |
| __all__ | __all__ | bioetl.composition.factories.__init__ | 1 |  |
| __all__ | __all__ | bioetl.composition.factories.data_source_factory | 1 |  |
| class | DataSourceFactory | bioetl.composition.factories.data_source_factory | 60 | public=create,list_providers |
| class | DataSourceRegistry | bioetl.composition.factories.data_source_factory | 134 | public=clear,contains,get,list_keys,list_providers |
| __all__ | __all__ | bioetl.composition.factories.dq_factory | 1 |  |
| class | DQServicesFactory | bioetl.composition.factories.dq_factory | 63 | public=create_bronze_analyzer,create_gold_analyzer,create_report_writer,create_silver_analyzer |
| class | HttpClientFactory | bioetl.composition.factories.http_client_factory | 162 | public=create_for_provider |
| __all__ | __all__ | bioetl.composition.factories.pipeline_factories | 1 |  |
| class | PipelineFactoryConfig | bioetl.composition.factories.pipeline_factories | 29 | bases=NamedTuple |
| constant | PIPELINE_CONFIGS | bioetl.composition.factories.pipeline_factories | 1 |  |
| function | _create_factory | bioetl.composition.factories.pipeline_factories | 26 | (config: PipelineFactoryConfig) |
| function | _register_factories_to | bioetl.composition.factories.pipeline_factories | 11 | (registry: PipelineRegistry) |
| function | get_factory | bioetl.composition.factories.pipeline_factories | 18 | (pipeline_name: str) |
| function | is_registered | bioetl.composition.factories.pipeline_factories | 10 | () |
| function | list_available_pipelines | bioetl.composition.factories.pipeline_factories | 7 | () |
| function | register_all_pipelines | bioetl.composition.factories.pipeline_factories | 40 | (registry: PipelineRegistry | None = None) |
| function | reset_registration | bioetl.composition.factories.pipeline_factories | 13 | () |
| __all__ | __all__ | bioetl.composition.factories.pipeline_factory | 1 |  |
| class | GenericPipelineFactory | bioetl.composition.factories.pipeline_factory | 192 | bases=Generic[TPipeline]; public=build_services,create_data_source,create_runner,create_transformer,create_with_services |
| function | _create_cached_bronze_data_source | bioetl.composition.factories.pipeline_factory | 52 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, cached_bronze: CachedBronzeContext) |
| function | _create_data_source | bioetl.composition.factories.pipeline_factory | 24 | (create_data_source_fn: DataSourceCreator, settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, pipeline_name: str = 'unknown') |
| function | _extract_dq_configs | bioetl.composition.factories.pipeline_factory | 34 | (yaml_config: PipelineYamlConfig | None) |
| function | _extract_dq_output_paths | bioetl.composition.factories.pipeline_factory | 37 | (yaml_config: PipelineYamlConfig | None) |
| function | _extract_entity_type | bioetl.composition.factories.pipeline_factory | 12 | (pipeline_name: str) |
| function | _extract_single_dq_config | bioetl.composition.factories.pipeline_factory | 30 | (sink: Any, layer_name: str, config_class: Any) |
| function | _get_layer_path | bioetl.composition.factories.pipeline_factory | 3 | (config: Any) |
| function | _has_flat_structure | bioetl.composition.factories.pipeline_factory | 3 | (config: Any) |
| function | assemble_runner | bioetl.composition.factories.pipeline_factory | 147 | (pipeline: BasePipeline, observability: ObservabilityBundle, silver_schema: pa.Schema | None, gold_schema: Any, strict_gold_validation: bool, yaml_config: PipelineYamlConfig | None = None) |
| function | build_pipeline_services | bioetl.composition.factories.pipeline_factory | 71 | (pipeline_name: str, create_data_source_fn: DataSourceCreator, settings: Settings, logger: LoggerPort, config: PipelineYamlConfig | None = None, filter_config: InputFilterConfig | None = None, tracer: TracingPort | None = None, dq_monitor: DQMonitorPort | None = None, metadata_coordinator: MetadataCoordinator | None = None, cached_bronze: CachedBronzeContext | None = None, silver_validator: Any = None) |
| function | create_pipeline_factory | bioetl.composition.factories.pipeline_factory | 19 | (pipeline_name: str, pipeline_class: type[TPipeline], provider: str, silver_schema: pa.Schema | None = None, gold_schema: Any = None, pandera_silver_schema: Any = None, transformer_class: type[BaseTransformer] | None = None) |
| function | create_pipeline_with_services | bioetl.composition.factories.pipeline_factory | 108 | (pipeline_name: str, pipeline_class: type[BasePipeline], provider: str, create_data_source_fn: DataSourceCreator, transformer_class: type[BaseTransformer] | None, run_id: RunID, runtime: RuntimeConfig, settings: Settings, logger: LoggerPort, config: PipelineYamlConfig | None = None, filter_config: InputFilterConfig | None = None, tracer: TracingPort | None = None, dq_monitor: DQMonitorPort | None = None, metrics: MetricsPort | None = None, cached_bronze: CachedBronzeContext | None = None, pandera_silver_schema: Any = None) |
| type_alias | TPipeline | bioetl.composition.factories.pipeline_factory | 1 |  |
| class | MetricsExtractor | bioetl.composition.factories.runner_factory | 35 | public=extract_metrics |
| class | RunnerFactory | bioetl.composition.factories.runner_factory | 76 | public=contains,create,list_pipelines |
| function | create_metrics_extractor | bioetl.composition.factories.runner_factory | 7 | () |
| function | create_runner_factory | bioetl.composition.factories.runner_factory | 12 | (registry: PipelineRegistry | None = None) |
| __all__ | __all__ | bioetl.composition.factories.services_factory | 1 |  |
| class | BaseServicesFactory | bioetl.composition.factories.services_factory | 240 | public=create_common_services |
| class | ServicesBuilder | bioetl.composition.factories.services_factory | 266 | public=create_batch_executor_from_pipeline,create_checkpoint_manager,create_record_processor,create_record_processor_from_pipeline |
| function | create_data_normalization_service | bioetl.composition.factories.services_factory | 32 | (config: DataNormalizationConfig | None = None) |
| function | extract_pipeline_callbacks | bioetl.composition.factories.services_factory | 44 | (pipeline: BasePipeline) |
| __all__ | __all__ | bioetl.composition.factories.storage | 1 |  |
| __all__ | __all__ | bioetl.composition.factories.storage_adapter | 1 |  |
| class | StorageAdapter | bioetl.composition.factories.storage_adapter | 616 | public=aclose,archive,cleanup_bronze,clear_csv,clear_delta,clear_gold,clear_silver,health_check,optimize,preview_cleanup,read_silver,vacuum,write_bronze,write_gold,write_gold_merged,write_silver,write_silver_merged |
| __all__ | __all__ | bioetl.composition.factories.storage_factory | 1 |  |
| class | StorageContext | bioetl.composition.factories.storage_factory | 8 |  |
| class | StorageFactory | bioetl.composition.factories.storage_factory | 294 | public=create |
| __all__ | __all__ | bioetl.composition.factories.transformer_factory | 1 |  |
| function | create_transformer | bioetl.composition.factories.transformer_factory | 62 | (provider: str, entity_type: str, tracer: TracingPort | None = None, metrics: MetricsPort | None = None, silver_filters: SilverFilterConfig | GoldFilterConfig | None = None, gold_filters: GoldFilterConfig | None = None, identity_service: IdentityService | None = None, pii_hasher: PiiHasherPort | None = None, data_normalizer: DataNormalizationPort | None = None) |
| function | get_transformer_class | bioetl.composition.factories.transformer_factory | 15 | (provider: str, entity_type: str) |
| function | register_all_transformers | bioetl.composition.factories.transformer_factory | 103 | () |
| function | register_transformer | bioetl.composition.factories.transformer_factory | 14 | (provider: str, entity_type: str, transformer_class: type[BaseTransformer]) |
| __all__ | __all__ | bioetl.composition.observability | 1 |  |
| class | ObservabilityBundle | bioetl.composition.observability | 86 | public=bind,create |
| class | ObservabilityContractError | bioetl.composition.observability | 6 | bases=Exception |
| __all__ | __all__ | bioetl.composition.providers.__init__ | 1 |  |
| function | _get_adapter_config | bioetl.composition.providers._config_helpers | 22 | (provider: str, default_page_size: int = 1000) |
| function | _get_batch_size_from_config | bioetl.composition.providers._config_helpers | 4 | (provider: str, default: int = 100) |
| function | _get_circuit_breaker_from_config | bioetl.composition.providers._config_helpers | 16 | (provider: str) |
| function | _get_factories | bioetl.composition.providers._config_helpers | 6 | () |
| function | _get_rate_limit_from_config | bioetl.composition.providers._config_helpers | 16 | (provider: str) |
| function | _get_source_config | bioetl.composition.providers._config_helpers | 15 | (provider: str) |
| function | _wrap_with_filter | bioetl.composition.providers._config_helpers | 18 | (data_source: DataSourcePort, filter_config: InputFilterConfig | None, logger: LoggerPort | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| constant | T | bioetl.composition.providers.decorators | 1 |  |
| function | register_provider | bioetl.composition.providers.decorators | 100 | (name: str, *, http_rate: float = 5.0, http_capacity: int = 10, requires_http_client: bool = True, requires_logger: bool = True, rate_overrides: dict[str, float] | None = None, custom_creator: AdapterCreator | None = None, **default_kwargs: Any) |
| function | ensure_providers_loaded | bioetl.composition.providers.loader | 8 | () |
| function | get_loaded_status | bioetl.composition.providers.loader | 3 | () |
| function | load_providers | bioetl.composition.providers.loader | 33 | (force: bool = False) |
| function | reset_loader | bioetl.composition.providers.loader | 5 | () |
| class | DataSourceCreator | bioetl.composition.providers.provider_registry | 29 | bases=Protocol |
| class | HttpConfig | bioetl.composition.providers.provider_registry | 14 |  |
| class | ProviderConfig | bioetl.composition.providers.provider_registry | 24 |  |
| class | ProviderRegistry | bioetl.composition.providers.provider_registry | 211 | public=clear,create_adapter,create_data_source,get,get_http_config,has_data_source_creator,is_registered,list_providers,register |
| function | _create_chembl_data_source | bioetl.composition.providers.registration | 48 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_crossref_data_source | bioetl.composition.providers.registration | 44 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_openalex_data_source | bioetl.composition.providers.registration | 44 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_pubchem_adapter | bioetl.composition.providers.registration | 33 | (http_client: UnifiedHTTPClient | None = None, logger: LoggerPort | None = None, settings: Settings | None = None, **kwargs: Any) |
| function | _create_pubchem_data_source | bioetl.composition.providers.registration | 16 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_pubmed_data_source | bioetl.composition.providers.registration | 28 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_semanticscholar_data_source | bioetl.composition.providers.registration | 51 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_uniprot_data_source | bioetl.composition.providers.registration | 19 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _create_uniprot_idmapping_data_source | bioetl.composition.providers.registration | 72 | (settings: Settings, pipeline_config: PipelineYamlConfig, logger: LoggerPort, filter_config: InputFilterConfig | None = None, metrics: MetricsPort | None = None, pipeline_name: str = 'unknown') |
| function | _validate_extraction_input_filter_overlap | bioetl.composition.providers.registration | 32 | (extraction_params: ExtractionParams, input_filter: InputFilterConfig, logger: LoggerPort) |
| function | register_all_providers | bioetl.composition.providers.registration | 174 | () |
| class | PipelineDefinition | bioetl.composition.registry | 14 | bases=NamedTuple |
| class | PipelineFactoryProtocol | bioetl.composition.registry | 35 | bases=Protocol; public=create_runner,create_with_services |
| class | PipelineRegistry | bioetl.composition.registry | 167 | public=clear,contains,get,list_keys,list_pipelines,register,register_factory |
| function | create_registry | bioetl.composition.registry | 10 | () |
| function | get_default_registry | bioetl.composition.registry | 10 | () |
| __all__ | __all__ | bioetl.composition.services.__init__ | 1 |  |
| class | MetadataCoordinator | bioetl.composition.services.metadata_coordinator | 435 | public=create_bronze_metadata,create_gold_metadata,create_silver_metadata,reset_environment_cache,run_context |
| function | _get_bioetl_version | bioetl.composition.services.metadata_coordinator | 12 | () |
| __all__ | __all__ | bioetl.composition.services.versioning | 1 |  |
| function | _normalize_for_hash | bioetl.composition.services.versioning | 24 | (obj: Any) |
| function | compute_config_hash | bioetl.composition.services.versioning | 35 | (config: PipelineYamlConfig | dict[str, Any]) |
| function | get_git_commit | bioetl.composition.services.versioning | 32 | () |
| function | get_pipeline_version | bioetl.composition.services.versioning | 34 | (config: PipelineYamlConfig | dict[str, Any] | None = None) |
| __all__ | __all__ | bioetl.composition.types | 1 |  |

### 1.5 Interfaces Layer
| Type | Name | Module | LOC | Details |
|------|------|--------|-----|---------|
| __all__ | __all__ | bioetl.interfaces.cli.__init__ | 1 |  |
| function | archive_command | bioetl.interfaces.cli.commands.archive | 25 | (table: str, target_path: str, remove_source: bool) |
| function | checkpoint | bioetl.interfaces.cli.commands.checkpoint | 2 | () |
| function | checkpoint_list | bioetl.interfaces.cli.commands.checkpoint | 12 | (pipeline: str) |
| function | bronze_cleanup_command | bioetl.interfaces.cli.commands.cleanup | 26 | (retention_days: int, dry_run: bool) |
| function | _config_to_dict | bioetl.interfaces.cli.commands.config | 13 | (config: Any) |
| function | config | bioetl.interfaces.cli.commands.config | 2 | () |
| function | list_pipelines_command | bioetl.interfaces.cli.commands.config | 17 | () |
| function | show_command | bioetl.interfaces.cli.commands.config | 28 | (pipeline: str, output_format: str) |
| function | show_settings_command | bioetl.interfaces.cli.commands.config | 43 | (output_format: str) |
| function | validate_command | bioetl.interfaces.cli.commands.config | 23 | (pipeline: str) |
| function | export_command | bioetl.interfaces.cli.commands.export | 93 | (table: str | None, list_tables: bool, preview: bool, output_format: str, layer: str, output: Path | None, limit: int | None, columns: str | None) |
| __all__ | __all__ | bioetl.interfaces.cli.commands.health | 1 |  |
| function | health | bioetl.interfaces.cli.commands.health | 2 | () |
| function | health_check | bioetl.interfaces.cli.commands.health | 64 | (provider: tuple[str, ...], output_json: bool) |
| function | health_server_command | bioetl.interfaces.cli.commands.health | 54 | (host: str, port: int) |
| __all__ | __all__ | bioetl.interfaces.cli.commands.health_server_integration | 1 |  |
| constant | DEFAULT_HEALTH_SERVER_PORT | bioetl.interfaces.cli.commands.health_server_integration | 1 |  |
| function | add_health_server_options | bioetl.interfaces.cli.commands.health_server_integration | 28 | (cmd: click.Command) |
| function | echo_health_server_info | bioetl.interfaces.cli.commands.health_server_integration | 10 | (enabled: bool, port: int, host: str = '127.0.0.1') |
| function | health_server_context | bioetl.interfaces.cli.commands.health_server_integration | 48 | (enabled: bool, host: str = '127.0.0.1', port: int = DEFAULT_HEALTH_SERVER_PORT) |
| function | check_command | bioetl.interfaces.cli.commands.lock | 27 | (pipeline: str, run_id: str) |
| function | lock | bioetl.interfaces.cli.commands.lock | 2 | () |
| function | release_command | bioetl.interfaces.cli.commands.lock | 33 | (pipeline: str, run_id: str, exclusive: bool) |
| function | maintenance | bioetl.interfaces.cli.commands.maintenance | 2 | () |
| __all__ | __all__ | bioetl.interfaces.cli.commands.metrics_server_integration | 1 |  |
| function | metrics_server_context | bioetl.interfaces.cli.commands.metrics_server_integration | 18 | () |
| __all__ | __all__ | bioetl.interfaces.cli.commands.quarantine | 1 |  |
| function | quarantine | bioetl.interfaces.cli.commands.quarantine | 6 | () |
| function | quarantine_inspect | bioetl.interfaces.cli.commands.quarantine | 21 | (pipeline: str, limit: int, error_code: str | None) |
| function | quarantine_purge | bioetl.interfaces.cli.commands.quarantine | 41 | (pipeline: str, older_than_days: int, dry_run: bool, force: bool) |
| function | quarantine_replay | bioetl.interfaces.cli.commands.quarantine | 43 | (pipeline: str, error_code: str | None, max_age_days: int, dry_run: bool) |
| function | quarantine_resolve | bioetl.interfaces.cli.commands.quarantine | 24 | (pipeline: str, payload_hash: str, status: str) |
| function | quarantine_stats | bioetl.interfaces.cli.commands.quarantine | 48 | (pipeline: str, output_json: bool) |
| function | _echo_run_result | bioetl.interfaces.cli.commands.run | 31 | (status: PipelineRunResult, error_message: str | None, run_id: str) |
| function | _map_status_to_exit_code | bioetl.interfaces.cli.commands.run | 35 | (status: PipelineRunResult, error_type: str | None) |
| function | _run_pipeline_async | bioetl.interfaces.cli.commands.run | 27 | (pipeline: str, options: RunOptions, health_server_enabled: bool = True, health_port: int = DEFAULT_HEALTH_SERVER_PORT) |
| function | run | bioetl.interfaces.cli.commands.run | 68 | (pipeline: str, run_type: str, resume: bool, limit: int | None, input_csv: str | None, filter_column: str | None, filter_field: str | None, dry_run: bool, yes: bool, vacuum_after_run: bool | None, vacuum_retention_days: int | None, debug: bool, health_server: bool, health_port: int, use_cached_bronze: bool, cached_bronze_date: str | None, cached_bronze_path: str | None) |
| __all__ | __all__ | bioetl.interfaces.cli.commands.run_all | 1 |  |
| class | BatchRunResult | bioetl.interfaces.cli.commands.run_all | 14 | public=all_succeeded |
| function | _determine_exit_code | bioetl.interfaces.cli.commands.run_all | 8 | (batch_result: BatchRunResult) |
| function | _echo_batch_summary | bioetl.interfaces.cli.commands.run_all | 17 | (result: BatchRunResult, dry_run: bool) |
| function | _filter_pipelines_by_provider | bioetl.interfaces.cli.commands.run_all | 5 | (provider: str) |
| function | _get_available_providers | bioetl.interfaces.cli.commands.run_all | 6 | () |
| function | _handle_destructive_confirmation | bioetl.interfaces.cli.commands.run_all | 20 | (run_type: str, pipelines: list[str], dry_run: bool, yes: bool) |
| function | _handle_list_only | bioetl.interfaces.cli.commands.run_all | 7 | (source: str, pipelines: list[str]) |
| function | _run_all_pipelines_async | bioetl.interfaces.cli.commands.run_all | 13 | (pipelines: list[str], options: RunOptions, health_server_enabled: bool = True, health_port: int = DEFAULT_HEALTH_SERVER_PORT) |
| function | _run_pipeline_async | bioetl.interfaces.cli.commands.run_all | 5 | (service: PipelineRunnerService, pipeline: str, options: RunOptions) |
| function | _run_pipelines_batch | bioetl.interfaces.cli.commands.run_all | 39 | (service: PipelineRunnerService, pipelines: list[str], options: RunOptions) |
| function | _show_run_preview | bioetl.interfaces.cli.commands.run_all | 10 | (source: str, pipelines: list[str], dry_run: bool) |
| function | _validate_provider | bioetl.interfaces.cli.commands.run_all | 12 | (provider: str) |
| function | run_all | bioetl.interfaces.cli.commands.run_all | 75 | (source: str, run_type: str, limit: int | None, dry_run: bool, yes: bool, list_only: bool, debug: bool, health_server: bool, health_port: int) |
| function | _run_composite_async | bioetl.interfaces.cli.commands.run_composite | 25 | (composite_name: str, runtime: CompositeRuntimeConfig, health_server_enabled: bool = True, health_port: int = DEFAULT_HEALTH_SERVER_PORT) |
| function | _run_composite_inner | bioetl.interfaces.cli.commands.run_composite | 33 | (composite_name: str, runtime: CompositeRuntimeConfig) |
| function | _validate_composite_name | bioetl.interfaces.cli.commands.run_composite | 7 | (_ctx: click.Context, _param: click.Parameter, value: str) |
| function | run_composite | bioetl.interfaces.cli.commands.run_composite | 78 | (composite: str, resume: bool, dry_run: bool, seed_limit: int | None, enrich_only: str | None, required_only: bool, force_enricher: str | None, use_cached_bronze: bool, cached_bronze_date: str | None, cached_bronze_path: str | None, cached_bronze_enrichers: bool | None, cached_bronze_dependencies: bool, debug: bool, health_server: bool, health_port: int) |
| __all__ | __all__ | bioetl.interfaces.cli.commands.run_helpers | 1 |  |
| function | _preview_cleanup_async | bioetl.interfaces.cli.commands.run_helpers | 8 | (pipeline: str) |
| function | get_runner_logger | bioetl.interfaces.cli.commands.run_helpers | 13 | (runner: PipelineRunner) |
| function | handle_destructive_run_confirmation | bioetl.interfaces.cli.commands.run_helpers | 30 | (pipeline: str, run_type: str, dry_run: bool, yes: bool) |
| function | show_cleanup_preview | bioetl.interfaces.cli.commands.run_helpers | 10 | (pipeline: str) |
| function | validate_pipeline_name | bioetl.interfaces.cli.commands.run_helpers | 21 | (_ctx: click.Context | None, _param: click.Parameter | None, value: str) |
| function | vacuum_all_command | bioetl.interfaces.cli.commands.vacuum | 35 | (retention_days: int, dry_run: bool, layer: str) |
| function | vacuum_command | bioetl.interfaces.cli.commands.vacuum | 31 | (table: str, retention_days: int, dry_run: bool) |
| __all__ | __all__ | bioetl.interfaces.cli.exit_codes | 1 |  |
| class | ExitCode | bioetl.interfaces.cli.exit_codes | 42 | bases=IntEnum |
| constant | EXCEPTION_EXIT_CODES | bioetl.interfaces.cli.exit_codes | 1 |  |
| function | get_exit_code_for_exception | bioetl.interfaces.cli.exit_codes | 23 | (exc: BaseException) |
| function | echo_checkpoint | bioetl.interfaces.cli.formatters | 7 | (checkpoint: str) |
| function | echo_cleanup_preview | bioetl.interfaces.cli.formatters | 23 | (preview: CleanupPreview) |
| function | echo_dry_run_prefix | bioetl.interfaces.cli.formatters | 7 | (message: str) |
| function | echo_error | bioetl.interfaces.cli.formatters | 11 | (message: str, detail: str | None = None) |
| function | echo_export_preview | bioetl.interfaces.cli.formatters | 41 | (preview: TablePreview) |
| function | echo_export_result | bioetl.interfaces.cli.formatters | 11 | (result: ExportResult) |
| function | echo_info | bioetl.interfaces.cli.formatters | 7 | (message: str) |
| function | echo_quarantine_record | bioetl.interfaces.cli.formatters | 10 | (record: dict[str, Any]) |
| function | echo_table_list | bioetl.interfaces.cli.formatters | 17 | (tables: list[TableInfo]) |
| function | echo_vacuum_all_summary | bioetl.interfaces.cli.formatters | 11 | (result: VacuumAllResult) |
| function | echo_vacuum_result | bioetl.interfaces.cli.formatters | 17 | (result: TableVacuumResult, dry_run: bool) |
| function | echo_warning | bioetl.interfaces.cli.formatters | 7 | (message: str) |
| function | format_bytes | bioetl.interfaces.cli.formatters | 13 | (b: int) |
| function | cli | bioetl.interfaces.cli.main | 2 | () |
| function | main | bioetl.interfaces.cli.main | 4 | () |
| __all__ | __all__ | bioetl.interfaces.http.__init__ | 1 |  |
| __all__ | __all__ | bioetl.interfaces.http.health_server | 1 |  |
| class | HealthServer | bioetl.interfaces.http.health_server | 262 | public=is_running,start,stop,uptime_seconds |
| function | run_health_server | bioetl.interfaces.http.health_server | 18 | (host: str = '0.0.0.0', port: int = 8080, health_monitor: HealthMonitorPort | None = None, logger: LoggerPort | None = None) |
| __all__ | __all__ | bioetl.interfaces.http.types | 1 |  |
| class | HealthResponse | bioetl.interfaces.http.types | 28 | public=http_status,to_json |
| __all__ | __all__ | bioetl.interfaces.observability | 1 |  |

## 2. Dead Code
### 2.1 DEAD объекты (0 ссылок)
| # | Object | Type | Layer | File |
|---|--------|------|-------|------|
| 1 | bioetl.domain.normalization._to_none_if_empty | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\normalization.py |
| 2 | bioetl.domain.transformations._normalize_date | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\transformations.py |
| 3 | bioetl.domain.transformations._normalize_datetime | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\transformations.py |
| 4 | bioetl.domain.transformations._normalize_dict | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\transformations.py |
| 5 | bioetl.domain.transformations._normalize_float | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\transformations.py |
| 6 | bioetl.domain.transformations._normalize_str | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\transformations.py |
| 7 | bioetl.domain.validation.validate_inchi_key | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\validation.py |
| 8 | bioetl.domain.validation.validate_publication_year | function | domain | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\domain\validation.py |
| 9 | bioetl.application.core.field_specs.pmid_fields | function | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\core\field_specs.py |
| 10 | bioetl.application.core.subcellular_fraction_data_source.SubcellularFractionDataSource | class | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\core\subcellular_fraction_data_source.py |
| 11 | bioetl.application.pipelines.pubchem.__init__.PubChemCompoundPipeline | class | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\pipelines\pubchem\__init__.py |
| 12 | bioetl.application.pipelines.pubmed.__init__.PubMedPublicationPipeline | class | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\pipelines\pubmed\__init__.py |
| 13 | bioetl.application.pipelines.pubmed.xml_parser.get_int | function | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\pipelines\pubmed\xml_parser.py |
| 14 | bioetl.application.pipelines.uniprot.__init__.UniProtProteinPipeline | class | application | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\pipelines\uniprot\__init__.py |
| 15 | bioetl.infrastructure.adapters.crossref.exceptions.CrossRefNotFoundError | class | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\crossref\exceptions.py |
| 16 | bioetl.infrastructure.adapters.crossref.exceptions.CrossRefRateLimitError | class | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\crossref\exceptions.py |
| 17 | bioetl.infrastructure.adapters.crossref.exceptions.CrossRefServiceUnavailableError | class | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\crossref\exceptions.py |
| 18 | bioetl.infrastructure.adapters.http.circuit_breaker.is_circuit_breaker_error | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\http\circuit_breaker.py |
| 19 | bioetl.infrastructure.adapters.http.rate_limiter.create_pubchem_bucket | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\http\rate_limiter.py |
| 20 | bioetl.infrastructure.adapters.http.rate_limiter.create_pubmed_bucket | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\adapters\http\rate_limiter.py |
| 21 | bioetl.infrastructure.observability.logging.create_logger | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\observability\logging.py |
| 22 | bioetl.infrastructure.observability.logging_config.reset_logging_config | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\observability\logging_config.py |
| 23 | bioetl.infrastructure.observability.metrics.MetricsCollector | class | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\observability\metrics.py |
| 24 | bioetl.infrastructure.serialization.encoders.reset_encoder_cache | function | infrastructure | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\infrastructure\serialization\encoders.py |
| 25 | bioetl.composition.bootstrap_logger.BootstrapLogger | class | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\bootstrap_logger.py |
| 26 | bioetl.composition.bootstrap_logger.reset_bootstrap_logger | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\bootstrap_logger.py |
| 27 | bioetl.composition.factories.pipeline_factories.get_factory | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\factories\pipeline_factories.py |
| 28 | bioetl.composition.factories.pipeline_factories.list_available_pipelines | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\factories\pipeline_factories.py |
| 29 | bioetl.composition.factories.pipeline_factories.reset_registration | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\factories\pipeline_factories.py |
| 30 | bioetl.composition.providers.loader.get_loaded_status | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\providers\loader.py |
| 31 | bioetl.composition.providers.loader.reset_loader | function | composition | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\providers\loader.py |
| 32 | bioetl.interfaces.cli.commands.checkpoint.checkpoint_list | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\checkpoint.py |
| 33 | bioetl.interfaces.cli.commands.config.list_pipelines_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\config.py |
| 34 | bioetl.interfaces.cli.commands.config.show_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\config.py |
| 35 | bioetl.interfaces.cli.commands.config.show_settings_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\config.py |
| 36 | bioetl.interfaces.cli.commands.config.validate_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\config.py |
| 37 | bioetl.interfaces.cli.commands.health.health_server_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\health.py |
| 38 | bioetl.interfaces.cli.commands.health_server_integration.add_health_server_options | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\health_server_integration.py |
| 39 | bioetl.interfaces.cli.commands.lock.check_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\lock.py |
| 40 | bioetl.interfaces.cli.commands.lock.release_command | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\lock.py |
| 41 | bioetl.interfaces.cli.commands.metrics_server_integration.metrics_server_context | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\metrics_server_integration.py |
| 42 | bioetl.interfaces.cli.commands.quarantine.quarantine_inspect | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\quarantine.py |
| 43 | bioetl.interfaces.cli.commands.quarantine.quarantine_purge | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\quarantine.py |
| 44 | bioetl.interfaces.cli.commands.quarantine.quarantine_replay | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\quarantine.py |
| 45 | bioetl.interfaces.cli.commands.quarantine.quarantine_resolve | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\quarantine.py |
| 46 | bioetl.interfaces.cli.commands.quarantine.quarantine_stats | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\commands\quarantine.py |
| 47 | bioetl.interfaces.cli.exit_codes.get_exit_code_for_exception | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\cli\exit_codes.py |
| 48 | bioetl.interfaces.http.health_server.run_health_server | function | interfaces | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\interfaces\http\health_server.py |

### 2.4 Orphan-модули (файлы без imports)
| # | File | LOC | Objects Defined |
|---|------|-----|----------------|
| 1 | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\application\core\subcellular_fraction_data_source.py | 518 | __all__, SubcellularFractionDataSource |
| 2 | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\bootstrap_logger.py | 144 | __all__, BootstrapLogger, get_bootstrap_logger, reset_bootstrap_logger |
| 3 | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\factories\storage_adapter.py | 652 | __all__, StorageAdapter |
| 4 | E:\g-drive\05_AI\github\BioactivityDataAcquisition2\src\bioetl\composition\factories\storage_factory.py | 341 | __all__, StorageContext, StorageFactory |

## 3. Duplicate Logic
### 3.1 Confirmed Duplicates (идентичная логика)
| # | Hash | LOC | Severity | Objects |
|---|------|-----|----------|---------|
| 1 | ad2e13b69c4f | 2 | LOW | bioetl.domain.types.BronzeRecord; bioetl.application.pipelines.chembl._pipelines.ChEMBLActivityPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLAssayParametersPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLAssayPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLCellLinePipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLCompoundRecordPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLMoleculePipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLProteinClassPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLPublicationPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLPublicationSimilarityPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLPublicationTermPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLSubcellularFractionPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLTargetComponentPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLTargetPipeline; bioetl.application.pipelines.chembl._pipelines.ChEMBLTissuePipeline; bioetl.application.pipelines.generic.GenericPipeline; bioetl.application.pipelines.pubchem.__init__.PubChemCompoundPipeline; bioetl.application.pipelines.pubmed.__init__.PubMedPublicationPipeline; bioetl.application.pipelines.uniprot.__init__.UniProtProteinPipeline; bioetl.infrastructure.adapters.filterable_mixin.FilterableStubMixin; bioetl.infrastructure.config.field_group_loader.FieldGroupLoadError; bioetl.infrastructure.schemas.pipeline_config.FilterColumnSchema; bioetl.infrastructure.schemas.pipeline_config.GoldColumnFilterConfig; bioetl.infrastructure.schemas.pipeline_config.GoldFiltersConfig; bioetl.infrastructure.schemas.pipeline_config.GoldListContainsFilterConfig; bioetl.infrastructure.schemas.pipeline_config.GoldListLengthFilterConfig; bioetl.infrastructure.schemas.pipeline_config.GoldRangeFilterConfig; bioetl.infrastructure.schemas.pipeline_config.InputFilterConfig; bioetl.composition.observability.ObservabilityContractError; bioetl.interfaces.cli.commands.checkpoint.checkpoint; bioetl.interfaces.cli.commands.config.config; bioetl.interfaces.cli.commands.health.health; bioetl.interfaces.cli.commands.lock.lock; bioetl.interfaces.cli.commands.maintenance.maintenance; bioetl.interfaces.cli.commands.quarantine.quarantine; bioetl.interfaces.cli.main.cli |

## 4. Dependency Map
### 4.1 Объекты с наибольшим fan-out (зависят от многих)
| Object | Dependencies Count |
|--------|-------------------|
| bioetl.composition.factories.pipeline_factories | 47 |
| bioetl.composition.factories.pipeline_factory | 31 |
| bioetl.composition.factories.services_factory | 27 |
| bioetl.domain.__init__ | 24 |
| bioetl.domain.ports.__init__ | 24 |
| bioetl.composition.factories.transformer_factory | 24 |
| bioetl.composition.bootstrap.runtime.composite | 21 |
| bioetl.application.core.__init__ | 20 |
| bioetl.composition.providers.registration | 20 |
| bioetl.domain.value_objects.__init__ | 18 |

### 4.2 Объекты с наибольшим fan-in (от них зависят многие)
| Object | Dependents Count |
|--------|-----------------|
| bioetl.domain.ports | 142 |
| bioetl.domain.types | 123 |
| bioetl.domain.context | 29 |
| bioetl.domain.exceptions | 29 |
| bioetl.domain.filtering | 28 |
| bioetl.domain.config | 24 |
| bioetl.infrastructure.config | 23 |
| bioetl.domain.models.metadata | 22 |
| bioetl.domain.entities | 18 |
| bioetl.domain.medallion | 18 |

### 4.3 Циклические зависимости внутри слоя
| # | Cycle | Files Involved |
|---|-------|----------------|
| – | – | – |

## 5. Рекомендации
- Заполнить рекомендации после детальной верификации.
