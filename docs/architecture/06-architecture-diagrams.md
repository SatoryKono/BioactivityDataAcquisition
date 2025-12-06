# Архитектурные диаграммы BioETL

## Текущая архитектура

```mermaid
graph TB
    subgraph "Interfaces Layer"
        CLI[CLI Runner]
    end
    
    subgraph "Application Layer"
        PB[PipelineBase]
        CPB[ChemblPipelineBase]
        AP[ActivityPipeline]
        DP[DocumentPipeline]
        MP[MoleculePipeline]
    end
    
    subgraph "Domain Layer"
        NM[NormalizerMixin]
        HS[HashService]
        VS[ValidationService]
        CN[Custom Normalizers]
        PS[Pandera Schemas]
    end
    
    subgraph "Infrastructure Layer"
        CC[ChEMBL Client]
        UW[UnifiedWriter]
        CR[Config Resolver]
        MW[Metadata Writer]
    end
    
    CLI --> PB
    PB --> CPB
    CPB --> AP
    CPB --> DP
    CPB --> MP
    CPB -.-> NM
    
    PB --> HS
    PB --> VS
    PB --> UW
    
    NM --> CN
    VS --> PS
    
    CPB --> CC
    UW --> MW
    PB --> CR
    
    style PB fill:#f9f,stroke:#333,stroke-width:2px
    style CPB fill:#f9f,stroke:#333,stroke-width:2px
    style NM fill:#ff9,stroke:#333,stroke-width:2px
```

## Проблемы текущей архитектуры

```mermaid
graph LR
    subgraph "Проблемы"
        P1[Тесная связанность]
        P2[Смешанные обязанности]
        P3[Row-by-row обработка]
        P4[Монолитность]
        P5[Отсутствие DI]
    end
    
    subgraph "Последствия"
        C1[Сложность тестирования]
        C2[Низкая производительность]
        C3[Сложность поддержки]
        C4[Невозможность масштабирования]
    end
    
    P1 --> C1
    P2 --> C3
    P3 --> C2
    P4 --> C4
    P5 --> C1
    
    style P1 fill:#f96,stroke:#333,stroke-width:2px
    style P2 fill:#f96,stroke:#333,stroke-width:2px
    style P3 fill:#f96,stroke:#333,stroke-width:2px
```

## Предлагаемая архитектура

```mermaid
graph TB
    subgraph "Interfaces"
        CLI2[CLI]
        API[REST API]
        MQ[Message Queue]
    end
    
    subgraph "Application Services"
        PO[Pipeline Orchestrator]
        DIC[DI Container]
        PM[Pipeline Monitor]
    end
    
    subgraph "Domain Services"
        subgraph "ETL Components"
            DE[Data Extractor]
            DT[Data Transformer]
            DV[Data Validator]  
            DW[Data Writer]
        end
        
        subgraph "Normalization"
            NF[Normalizer Factory]
            NS1[ID Strategy]
            NS2[Chemical Strategy]
            NS3[Numeric Strategy]
        end
        
        subgraph "Integrity"
            HS2[Hash Service]
            DS[Dedup Service]
        end
    end
    
    subgraph "Infrastructure"
        subgraph "Data Access"
            AC[Async ChEMBL Client]
            CS[Cache Service]
            SR[Stream Reader]
        end
        
        subgraph "Output"
            AW[Atomic Writer]
            MW2[Metadata Writer]
        end
        
        subgraph "Monitoring"
            MT[Metrics Collector]
            TR[Tracer]
        end
    end
    
    CLI2 --> PO
    API --> PO
    MQ --> PO
    
    PO --> DIC
    DIC --> DE
    DIC --> DT
    DIC --> DV
    DIC --> DW
    
    DE --> AC
    DE --> SR
    DT --> NF
    NF --> NS1
    NF --> NS2
    NF --> NS3
    
    DT --> HS2
    DT --> DS
    
    DW --> AW
    DW --> MW2
    
    PO --> PM
    PM --> MT
    PM --> TR
    
    AC --> CS
    
    style PO fill:#9f9,stroke:#333,stroke-width:2px
    style DIC fill:#9f9,stroke:#333,stroke-width:2px
    style NF fill:#9ff,stroke:#333,stroke-width:2px
```

## Поток данных в новой архитектуре

```mermaid
sequenceDiagram
    participant CLI
    participant Orchestrator
    participant DIContainer
    participant Extractor
    participant Transformer
    participant Validator
    participant Writer
    participant Monitor
    
    CLI->>Orchestrator: run_pipeline(config)
    Orchestrator->>DIContainer: resolve_dependencies()
    DIContainer-->>Orchestrator: services
    
    Orchestrator->>Monitor: start_pipeline_span()
    
    par Extraction
        Orchestrator->>Extractor: extract_data()
        Extractor-->>Orchestrator: DataFrame chunks
    and Monitoring
        Monitor->>Monitor: collect_metrics()
    end
    
    loop For each chunk
        Orchestrator->>Transformer: transform(chunk)
        Note over Transformer: Vectorized operations
        Transformer-->>Orchestrator: transformed_chunk
        
        Orchestrator->>Validator: validate(chunk)
        Validator-->>Orchestrator: validated_chunk
        
        Orchestrator->>Writer: write(chunk)
        Writer-->>Orchestrator: write_result
    end
    
    Orchestrator->>Monitor: end_pipeline_span()
    Monitor-->>CLI: metrics_report
    Orchestrator-->>CLI: pipeline_result
```

## Стратегия миграции

```mermaid
graph LR
    subgraph "Фаза 1"
        A1[Текущая архитектура]
        A2[Выделение стратегий]
        A3[Разделение PipelineBase]
    end
    
    subgraph "Фаза 2"
        B1[Векторизация]
        B2[Стриминг]
        B3[Кеширование]
    end
    
    subgraph "Фаза 3"
        C1[DI Container]
        C2[Async I/O]
        C3[Параллелизация]
    end
    
    subgraph "Фаза 4"
        D1[Message Queue]
        D2[Мониторинг]
        D3[Целевая архитектура]
    end
    
    A1 --> A2
    A2 --> A3
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2
    D2 --> D3
    
    style A1 fill:#f96,stroke:#333,stroke-width:2px
    style D3 fill:#9f9,stroke:#333,stroke-width:2px
```

## Компонентная диаграмма новой архитектуры

```mermaid
C4Component
    title Component diagram for BioETL System

    Container_Boundary(app, "Application") {
        Component(orchestrator, "Pipeline Orchestrator", "Python", "Coordinates ETL stages")
        Component(di, "DI Container", "dependency-injector", "Manages dependencies")
        Component(monitor, "Pipeline Monitor", "Python", "Tracks performance")
    }
    
    Container_Boundary(domain, "Domain") {
        Component(extractor, "Data Extractor", "Python", "Extracts data from sources")
        Component(transformer, "Data Transformer", "Python", "Transforms and normalizes")
        Component(validator, "Data Validator", "Pandera", "Validates schemas")
        Component(writer, "Data Writer", "Python", "Writes results")
    }
    
    Container_Boundary(infra, "Infrastructure") {
        ComponentDb(chembl, "ChEMBL API", "REST API", "Source data")
        ComponentDb(storage, "File System", "CSV/Parquet", "Output storage")
        Component(cache, "Redis Cache", "Redis", "Caches API responses")
    }
    
    Rel(orchestrator, di, "Uses")
    Rel(orchestrator, monitor, "Reports to")
    Rel(di, extractor, "Provides")
    Rel(di, transformer, "Provides")
    Rel(di, validator, "Provides")
    Rel(di, writer, "Provides")
    
    Rel(extractor, chembl, "Fetches from")
    Rel(extractor, cache, "Caches in")
    Rel(writer, storage, "Writes to")
```

## Сравнение производительности

```mermaid
graph TD
    subgraph "Текущая производительность"
        CP1[100K records: 10 min]
        CP2[1M records: 100 min]
        CP3[10M records: Out of Memory]
    end
    
    subgraph "После оптимизации"
        NP1[100K records: 2 min]
        NP2[1M records: 20 min]
        NP3[10M records: 200 min]
    end
    
    subgraph "Improvements"
        I1[5x faster for small datasets]
        I2[5x faster for medium datasets]
        I3[Can handle large datasets]
    end
    
    CP1 -.-> NP1
    CP2 -.-> NP2
    CP3 -.-> NP3
    
    NP1 --> I1
    NP2 --> I2
    NP3 --> I3
    
    style I1 fill:#9f9,stroke:#333,stroke-width:2px
    style I2 fill:#9f9,stroke:#333,stroke-width:2px
    style I3 fill:#9f9,stroke:#333,stroke-width:2px
```
