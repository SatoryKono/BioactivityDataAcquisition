# Class Diagrams — Application Layer

Устаревшие inline-диаграммы удалены. Храните актуальные схемы application-слоя в `docs/architecture/diagrams/class/` (текстовые Mermaid/PlantUML по политике `docs/architecture/diagrams/00-diagramming-policy.md`).
# Class Diagrams - Application Layer

Диаграммы классов для слоя Application (bioetl.application).

## 1. Pipeline Base Hierarchy

```mermaid
---
id: e95de373-b6d8-46a5-8621-9e6ad6b48ff6
---
classDiagram
    class PipelineBase {
        <<abstract>>
        -_config: PipelineConfig
        -_logger: LoggerAdapterABC
        -_validation_service: ValidationService
        -_hash_service: HashService
        -_output_writer: UnifiedOutputWriter
        -_extractor: ExtractorABC
        -_transformer: TransformerABC
        -_hooks: list[PipelineHookABC]
        -_error_policy: ErrorPolicyABC
        +run(output_path, dry_run) RunResult
        +extract()* DataFrame
        +transform()* DataFrame
        +validate(df) DataFrame
        +write(df, path) WriteResult
        #_process_chunk()
        #_execute_with_error_policy()
    }

    class ChemblPipelineBase {
        +get_database_version() str | None
        -_build_extractor() ExtractorABC
        -_build_transformer() TransformerABC
    }

    class ChemblEntityPipeline {
        +ID_COLUMN: str
        +API_FILTER_KEY: str
    }

    PipelineBase <|-- ChemblPipelineBase
    ChemblPipelineBase <|-- ChemblEntityPipeline
```

## 2. Pipeline Container

```mermaid
classDiagram
    class PipelineContainer {
        -config: PipelineConfig
        -_schema_registry: SchemaRegistry
        -_logger: LoggerAdapterABC
        -_hooks: list[PipelineHookABC]
        -_error_policy: ErrorPolicyABC
        +get_logger() LoggerAdapterABC
        +get_validation_service() ValidationService
        +get_output_writer() UnifiedOutputWriter
        +get_normalization_service() NormalizationService
        +get_record_source(extraction_service, limit) RecordSource
        +get_extraction_service() ExtractionServiceABC
        +get_hash_service() HashService
        +get_hooks() list[PipelineHookABC]
        +get_error_policy() ErrorPolicyABC
        +get_post_transformer(version_provider) TransformerABC
    }

    class ValidationService {
        +validate(df, entity_name) DataFrame
    }

    class UnifiedOutputWriter {
        +write_result(df, path, context) WriteResult
    }

    class HashService {
        +add_hash_columns(df, keys) DataFrame
    }

    PipelineContainer --> ValidationService : creates
    PipelineContainer --> UnifiedOutputWriter : creates
    PipelineContainer --> HashService : creates
```

## 3. Pipeline Orchestrator

```mermaid
classDiagram
    class PipelineOrchestrator {
        -_pipeline_name: str
        -_config: PipelineConfig
        -_container_factory: Callable
        +build_pipeline(limit) PipelineBase
        +run_pipeline(dry_run, limit) RunResult
        +run_in_background(dry_run, limit, executor) Future[RunResult]
        -_execute_in_subprocess(pipeline_name, config_payload, dry_run, limit) RunResult
    }

    class PipelineContainer {
        +get_logger() LoggerAdapterABC
        +get_validation_service() ValidationService
    }

    class PipelineBase {
        +run(output_path, dry_run) RunResult
    }

    class RunResult {
        +success: bool
        +row_count: int
        +duration_sec: float
    }

    PipelineOrchestrator --> PipelineContainer : uses
    PipelineOrchestrator --> PipelineBase : creates
    PipelineOrchestrator --> RunResult : returns
```

## 4. Pipeline Hooks

```mermaid
classDiagram
    class PipelineHookABC {
        <<abstract>>
        +on_stage_start(stage, context)*
        +on_stage_end(stage, result)*
        +on_error(stage, error)*
    }

    class LoggingPipelineHookImpl {
        -_logger: LoggerAdapterABC
        +on_stage_start(stage, context)
        +on_stage_end(stage, result)
        +on_error(stage, error)
    }

    class ErrorPolicyABC {
        <<abstract>>
        +handle(error, context)* ErrorAction
        +should_retry(error)* bool
    }

    class FailFastErrorPolicyImpl {
        +handle(error, context) ErrorAction
        +should_retry(error) bool
    }

    class ContinueOnErrorPolicyImpl {
        +handle(error, context) ErrorAction
        +should_retry(error) bool
    }

    PipelineHookABC <|-- LoggingPipelineHookImpl
    ErrorPolicyABC <|-- FailFastErrorPolicyImpl
    ErrorPolicyABC <|-- ContinueOnErrorPolicyImpl
```

## 5. Pipeline Contracts

```mermaid
classDiagram
    class ExtractorABC {
        <<abstract>>
        +extract()* DataFrame
        +iter_chunks()* Iterable[DataFrame]
    }

    class LoaderABC {
        <<abstract>>
        +load()* DataFrame
    }

    class ChemblExtractorImpl {
        -_extraction_service: ExtractionServiceABC
        -_record_source: RecordSource
        +extract() DataFrame
        +iter_chunks() Iterable[DataFrame]
    }

    class TransformerABC {
        <<abstract>>
        +apply(df, context)* DataFrame
    }

    class ChemblTransformerImpl {
        -_normalization_service: NormalizationService
        +apply(df, context) DataFrame
    }

    ExtractorABC <|-- ChemblExtractorImpl
    TransformerABC <|-- ChemblTransformerImpl
```

## 6. Pipeline Registry

```mermaid
classDiagram
    class PipelineRegistry {
        -_pipelines: dict[str, Type[PipelineBase]]
        +register(name, pipeline_class)
        +get(name) Type[PipelineBase]
        +list_all() list[str]
    }

    class PipelineBase {
        <<abstract>>
    }

    class ChemblEntityPipeline {
    }

    PipelineRegistry --> PipelineBase : stores
    PipelineRegistry ..> ChemblEntityPipeline : registers
```

## 7. Extraction Service

```mermaid
classDiagram
    class ExtractionServiceABC {
        <<abstract>>
        +extract_all()* DataFrame
        +extract_by_ids(ids)* DataFrame
        +extract_by_filter(filter_params)* DataFrame
    }

    class ChemblExtractionServiceImpl {
        -_client: DataClientABC
        -_config: PipelineConfig
        +extract_all() DataFrame
        +extract_by_ids(ids) DataFrame
        +extract_by_filter(filter_params) DataFrame
        -_fetch_paginated(request)
    }

    class DataClientABC {
        <<abstract>>
        +fetch_one(id)
        +fetch_many(ids)
        +iter_pages(request)
    }

    ExtractionServiceABC <|-- ChemblExtractionServiceImpl
    ChemblExtractionServiceImpl --> DataClientABC : uses
```

## 8. Pipeline Stages

```mermaid
classDiagram
    class StageABC {
        <<abstract>>
        +execute(context)* StageResult
        +validate(context)* bool
    }

    class ExtractStage {
        -_extractor: ExtractorABC
        +execute(context) StageResult
    }

    class TransformStage {
        -_transformer: TransformerABC
        +execute(context) StageResult
    }

    class ValidateStage {
        -_validation_service: ValidationService
        +execute(context) StageResult
    }

    class WriteStage {
        -_writer: UnifiedOutputWriter
        +execute(context) StageResult
    }

    StageABC <|-- ExtractStage
    StageABC <|-- TransformStage
    StageABC <|-- ValidateStage
    StageABC <|-- WriteStage
```

## 9. Pipeline Factory

```mermaid
classDiagram
    class PipelineFactory {
        +create_pipeline(pipeline_name, config) PipelineBase
        -_build_container(config) PipelineContainer
        -_resolve_pipeline_class(name) Type[PipelineBase]
    }

    class PipelineContainer {
        +get_logger() LoggerAdapterABC
        +get_validation_service() ValidationService
    }

    class PipelineBase {
        <<abstract>>
    }

    class ChemblEntityPipeline {
    }

    PipelineFactory --> PipelineContainer : uses
    PipelineFactory --> PipelineBase : creates
    PipelineFactory ..> ChemblEntityPipeline : instantiates
```

## 10. Pipeline Execution Flow

```mermaid
classDiagram
    class PipelineBase {
        -_config: PipelineConfig
        -_extractor: ExtractorABC
        -_transformer: TransformerABC
        -_validation_service: ValidationService
        -_output_writer: UnifiedOutputWriter
        -_hooks: list[PipelineHookABC]
        +run(output_path, dry_run) RunResult
        #_process_chunk() DataFrame
        #_execute_stage(stage, func) Any
    }

    class RunContext {
        +start_time: datetime
        +stage: str
        +chunk_index: int
    }

    class StageResult {
        +stage: str
        +success: bool
        +row_count: int
        +duration_sec: float
    }

    class RunResult {
        +success: bool
        +row_count: int
        +duration_sec: float
        +stages: list[StageResult]
    }

    PipelineBase --> RunContext : creates
    PipelineBase --> StageResult : produces
    PipelineBase --> RunResult : returns
```

