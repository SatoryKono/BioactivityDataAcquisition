
# Архитектурные диаграммы

Устаревшие inline-блоки удалены. Актуальные диаграммы хранятся в текстовых источниках согласно политике:

- `docs/architecture/diagrams/flow/high-level-architecture.mmd`
- `docs/architecture/diagrams/class/pipeline-class-structure.mmd`
- `docs/architecture/diagrams/sequence/pipeline-run-sequence.mmd`
- `docs/architecture/diagrams/flow/pipeline-error-flowchart.mmd`
- `docs/architecture/diagrams/class/client-architecture-three-layer.mmd`
- `docs/architecture/diagrams/flow/domain-services-transform.mmd`
- `docs/architecture/diagrams/flow/project-package-structure.mmd`

Полные правила и стиль: `docs/architecture/diagrams/00-diagramming-policy.md`.

## 1. High-Level Architecture (Hexagonal)

Диаграмма отображает архитектуру Ports & Adapters, где доменная логика (Core) изолирована от внешнего мира (Infrastructure/Interfaces).

```mermaid
graph TB
    subgraph Interfaces ["Interfaces (Driving)"]
        CLI[CLI App]
        RestAPI[REST Server]
        MQ[MQ Listener]
    end

    subgraph Infrastructure ["Infrastructure (Driven)"]
        subgraph Input
            ChEMBL[ChEMBL Client]
            PubChem[PubChem Client]
        end
        subgraph Output
            Writer[Unified Output Writer]
            Logger[Unified Logger]
        end
        subgraph Config
            CfgLoad[Config Loader]
            Pydantic[Pydantic Models]
        end
    end

    subgraph Application ["Application Layer"]
        Pipeline[Pipeline Orchestrator]
        Hooks[Pipeline Hooks]
    end

    subgraph Domain ["Domain Layer (Core)"]
        Validation[Validation Service]
        Normalization[Normalization Service]
        Hashing[Hash Service]
        Schemas[Pandera Schemas]
    end

    CLI -->|Calls| Pipeline
    Pipeline -->|Uses| Validation
    Pipeline -->|Uses| Normalization
    Pipeline -->|Uses| Hashing
    
    Validation -->|Validates| Schemas
    Normalization -.->|Uses| Schemas

    Pipeline -->|Uses| ChEMBL
    Pipeline -->|Uses| Writer
    Pipeline -->|Uses| Logger
    Pipeline -->|Configures| CfgLoad

    style Domain fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Application fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Infrastructure fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Interfaces fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

## 2. Pipeline Class Structure

Детальная диаграмма классов пайплайна и связанных сервисов.

```mermaid
classDiagram
    %% Core Abstractions
    class PipelineBase {
        <<Abstract>>
        +_config: PipelineConfig
        +_logger: LoggerAdapterABC
        +_validation_service: ValidationService
        +_hash_service: HashService
        +_output_writer: UnifiedOutputWriter
        +_hooks: list[PipelineHookABC]
        +_error_policy: ErrorPolicyABC
        +run(output_path, dry_run) RunResult
        +iter_chunks() Iterable[DataFrame]
        +extract()* DataFrame
        +transform()* DataFrame
        +validate(df) DataFrame
        +write(df, path) WriteResult
        #_process_chunk()
        #_execute_with_error_policy()
    }

    class ChemblEntityPipeline {
        +ID_COLUMN: str
        +API_FILTER_KEY: str
        +get_database_version()
    }

    %% Services
    class ValidationService {
        -_schema_provider: SchemaProviderABC
        +get_schema(entity_name)
        +get_schema_columns(entity_name)
        +validate(df, entity_name)
    }

    class HashService {
        -_hasher: HasherABC
        +add_hash_columns(df, keys)
        +add_index_column(df)
        +add_database_version_column(df, version)
        +add_fulldate_column(df)
    }

    class UnifiedOutputWriter {
        -_writer: WriterABC
        -_metadata_writer: MetadataWriterABC
        -_atomic_op: AtomicFileOperation
        +write_result(df, path, context)
        #_stable_sort(df)
        #_apply_column_order(df)
    }

    %% Interfaces
    class PipelineHookABC {
        <<Interface>>
        +on_stage_start(stage, context)
        +on_stage_end(stage, result)
        +on_error(stage, error)
    }

    class ErrorPolicyABC {
        <<Interface>>
        +handle(error, context) ErrorAction
        +should_retry(error) bool
    }

    %% Relations
    PipelineBase <|-- ChemblEntityPipeline
    PipelineBase o-- ValidationService : uses
    PipelineBase o-- HashService : uses
    PipelineBase o-- UnifiedOutputWriter : uses
    PipelineBase o-- PipelineHookABC : has many
    PipelineBase o-- ErrorPolicyABC : uses
    
    ValidationService ..> PipelineBase : validates data
    HashService ..> PipelineBase : enriches data
    UnifiedOutputWriter ..> PipelineBase : persists data
```

## 3. Pipeline Execution Flow (Sequence)

Диаграмма последовательности выполнения метода `Pipeline.run()`.

```mermaid
---
id: e998049b-4c36-4c31-a209-1942516129e7
---
sequenceDiagram
    autonumber
    participant User as CLI/User
    participant Pipe as Pipeline
    participant Hooks as PipelineHooks
    participant Extr as Extractor (Source)
    participant Trans as Transformer
    participant Val as Validator
    participant Writer as UnifiedWriter
    participant Meta as MetadataWriter

    User->>Pipe: run(output_path, dry_run=False)
    activate Pipe
    
    Pipe->>Pipe: Initialize RunContext
    Pipe->>Hooks: on_stage_start("extract")
    
    loop For each Chunk
        Pipe->>Extr: extract() (iter_chunks)
        activate Extr
        Extr-->>Pipe: raw_chunk (DataFrame)
        deactivate Extr
        
        Pipe->>Hooks: on_stage_start("transform")
        Pipe->>Trans: transform(raw_chunk)
        activate Trans
        Trans-->>Pipe: transformed_df
        deactivate Trans
        
        Pipe->>Hooks: on_stage_start("validate")
        Pipe->>Val: validate(transformed_df)
        activate Val
        Val-->>Pipe: validated_df
        deactivate Val
        
        Pipe->>Pipe: Collect validated chunk
    end

    Pipe->>Hooks: on_stage_end("extract")
    Pipe->>Hooks: on_stage_end("transform")
    Pipe->>Hooks: on_stage_end("validate")

    alt Not Dry Run
        Pipe->>Hooks: on_stage_start("write")
        Pipe->>Writer: write_result(all_data, output_path)
        activate Writer
        Writer->>Writer: Stable Sort & Reorder
        Writer->>Writer: Atomic Write (.tmp -> .csv)
        Writer->>Writer: Compute Checksum
        Writer->>Meta: write_meta(meta.yaml)
        Writer-->>Pipe: WriteResult
        deactivate Writer
        Pipe->>Hooks: on_stage_end("write")
    else Dry Run
        Pipe->>Pipe: Skip Write
    end

    Pipe-->>User: RunResult (Stats, Meta)
    deactivate Pipe
```

## 4. Execution Logic & Error Handling (Flowchart)

Логика управления потоком выполнения и обработки ошибок.

```mermaid
---
id: 3b5cfac9-48da-4eae-befc-028c206888ef
<!-- [MermaidChart: e717271c-e2a8-4f0e-870e-ee541bd17788] -->
---
flowchart TD
    Start([Start Run]) --> Init[Init Context & Reset Services]
    Init --> ExtractStart[Notify Extract Start]
    ExtractStart --> ChunkLoop{Has Next Chunk?}
    
    %% Extraction Loop
    ChunkLoop -- Yes --> ExtractExec[Execute extract()]
    ExtractExec -- Success --> TransformStart[Notify Transform Start]
    ExtractExec -- Error --> ErrHandler{Error Policy}
    
    ErrHandler -- Retry --> RetryChk{Retries Left?}
    RetryChk -- Yes --> ExtractExec
    RetryChk -- No --> FailAction
    
    ErrHandler -- Skip --> LogSkip[Log Skip]
    LogSkip --> ChunkLoop
    
    ErrHandler -- Fail --> FailAction[Raise PipelineStageError]
    FailAction --> EndFail([Run Failed])

    %% Transformation
    TransformStart --> TransExec[Execute transform()]
    TransExec -- Success --> ValidateStart[Notify Validate Start]
    TransExec -- Error --> ErrHandler
    
    %% Validation
    ValidateStart --> ValExec[Execute validate()]
    ValExec -- Success --> Accumulate[Accumulate Chunk]
    ValExec -- Error --> ErrHandler
    
    Accumulate --> ChunkLoop
    
    %% Post-Loop
    ChunkLoop -- No --> NotifyEnds[Notify Stages End]
    NotifyEnds --> DryRunChk{Dry Run?}
    
    %% Write Stage
    DryRunChk -- No --> WriteStart[Notify Write Start]
    WriteStart --> WriteExec[Execute write()]
    WriteExec --> MetaGen[Generate Metadata]
    MetaGen --> NotifyWriteEnd[Notify Write End]
    NotifyWriteEnd --> SuccessResult
    
    DryRunChk -- Yes --> DryRunMeta[Generate DryRun Metadata]
    DryRunMeta --> SuccessResult
    
    SuccessResult([Run Success])
```

## 5. Client Architecture (Three-Layer Pattern)

Реализация паттерна Contract -> Factory -> Implementation для внешних интеграций.

```mermaid
classDiagram
    class SourceClientABC {
        <<Interface>>
        +fetch_one(id)
        +fetch_many(ids)
        +iter_pages(request)
        +metadata()
    }

    class RequestBuilderABC {
        <<Interface>>
        +build(params)
        +with_pagination(offset, limit)
    }

    class ResponseParserABC {
        <<Interface>>
        +parse(response)
        +extract_metadata(response)
    }

    class ChemblClientHTTPImpl {
        -http_session: ClientSession
        -rate_limiter: RateLimiterABC
        -retry_policy: RetryPolicyABC
        +fetch_one(id)
        +fetch_many(ids)
        +iter_pages(request)
    }

    class ChemblClientFactory {
        +create_client(config) SourceClientABC
        +create_default() SourceClientABC
    }

    SourceClientABC <|-- ChemblClientHTTPImpl
    ChemblClientFactory ..> SourceClientABC : creates
    ChemblClientFactory ..> ChemblClientHTTPImpl : instantiates

    ChemblClientHTTPImpl *-- RequestBuilderABC : uses
    ChemblClientHTTPImpl *-- ResponseParserABC : uses
    ChemblClientHTTPImpl *-- RateLimiterABC : uses
    ChemblClientHTTPImpl *-- RetryPolicyABC : uses
```

## 6. Domain Services & Transform

Взаимодействие сервисов трансформации и валидации данных.

```mermaid
---
id: 55f41c2b-cfd6-431b-9a93-85e8bffc9a9c
---
graph TD
    subgraph "Transformers"
        T_Chain[TransformerChain]
        T_Hash[HashColumnsTransformer]
        T_Index[IndexColumnTransformer]
        T_Date[FulldateTransformer]
        T_ABC[<<TransformerABC>>]
    end

    subgraph "Services"
        HS[HashService]
        VS[ValidationService]
        NS[NormalizationService]
    end

    subgraph "Schemas"
        PS[PanderaValidator]
        Registry[Schema Registry]
    end

    Pipeline[Pipeline] --> T_Chain
    T_Chain --> T_Hash
    T_Chain --> T_Index
    T_Chain --> T_Date

    T_Hash -- uses --> HS[HashService]
    T_Index -- uses --> HS[HashService]

    Pipeline -- validates result --> VS[ValidationService]
    Pipeline -- normalizes values --> NS[NormalizationService]

    VS -- delegates --> PS[PanderaValidator]
    PS -- lookups schema --> Registry[Schema Registry]
    NS -- lookups rules --> Registry[Schema Registry]
```

## 7. Project Component Structure (Package Diagram)

Структура пакетов проекта и их зависимости, отражающие Clean Architecture.

```mermaid
---
id: eba65a67-a730-4b5a-b14d-365c0db29ed4
---
flowchart LR
  subgraph User["**Пользователь / CLI**"]
    CLI["**CLI** *main.py*"]
  end
  subgraph Application["**Application Layer** *(Оркестрация)*"]
    Pipelines["**Pipelines** *bioetl.application.pipelines.chembl*"]
    Runtime["**Pipeline Runtime / Runner** *bioetl.application.runtime*"]
  end
  subgraph Domain["**Domain Layer**"]
    DomainCore["**Domain Models & Transformations** *bioetl.domain.***"]
    Schemas["**Pandera Schemas** *bioetl.schemas.***"]
    Services["**Domain Services** *Normalization, Validation Facades*"]
  end
  subgraph Infrastructure["**Infrastructure Layer**"]
    Clients["**ChEMBL Clients** *bioetl.infrastructure.clients.chembl*"]
    Output["**Writers &amp; Storage** *bioetl.infrastructure.output*"]
    Logging["**Unified Logger** *bioetl.infrastructure.logging*"]
    Config["**Config / Resolver** *bioetl.infrastructure.config*"]
    QC["**QC / Golden Data** *bioetl.infrastructure.qc*"]
  end
  subgraph Interfaces["**Interfaces (Ports)**"]
    IF_Pipeline["**PipelineBase**, **ChemblPipelineBase** *bioetl.application.pipelines.base*"]
    IF_Client["**BaseClient**, **SourceClientABC** *bioetl.interfaces.clients*"]
    IF_Logger["**LoggerAdapterABC** *bioetl.interfaces.logging*"]
    IF_Writer["**WriterABC**, **UnifiedOutputWriterABC** *bioetl.interfaces.output*"]
    IF_Validator["**ValidatorABC** *bioetl.interfaces.validation*"]
  end
  CLI --> Runtime
  Runtime --> Pipelines
  Pipelines --> IF_Pipeline
  Pipelines --> IF_Client
  Pipelines --> IF_Writer
  Pipelines --> IF_Validator
  Pipelines --> IF_Logger
  Pipelines --> Config
  Pipelines --> QC
  IF_Pipeline --> DomainCore
  IF_Pipeline --> Schemas
  IF_Pipeline --> Services
  IF_Client --> Clients
  Clients --> ext_api["**ChEMBL REST API**"]
  IF_Writer --> Output
  Output --> fs["**Файловая система** (CSV/Parquet, metadata)"]
  IF_Validator --> Services
  Services --> Schemas
  IF_Logger --> Logging

  ext_api:::ext
  fs:::ext
  classDef default font-size:16px
  classDef ext fill:#fff,border:#999,stroke-dasharray:5 5,font-size:20px
  style Application fill:#FFFFFF
  style Interfaces fill:transparent
  style Domain fill:#FFFFFF
  style Infrastructure fill:#FFFFFF
```
