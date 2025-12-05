# Component Diagram

Диаграмма компонентов системы BioETL, показывающая основные компоненты и их взаимодействие.

```mermaid
graph TB
    subgraph "Interfaces Layer"
        CLI[CLI Application<br/>bioetl.interfaces.cli]
        REST[REST API Server<br/>bioetl.interfaces.rest]
        MQ[MQ Listener<br/>bioetl.interfaces.mq]
    end

    subgraph "Application Layer"
        ORCH[Pipeline Orchestrator<br/>bioetl.application.orchestrator]
        CONT[Pipeline Container<br/>bioetl.application.container]
        PBASE[Pipeline Base<br/>bioetl.application.pipelines.base]
        CPBASE[ChEMBL Pipeline Base<br/>bioetl.application.pipelines.chembl.base]
        ENTITY[Entity Pipelines<br/>Activity, Assay, Document, etc.]
        EXTRACT[Extraction Service<br/>bioetl.application.services]
        HOOKS[Pipeline Hooks<br/>bioetl.application.pipelines.hooks]
    end

    subgraph "Domain Layer"
        VALID[Validation Service<br/>bioetl.domain.validation]
        NORM[Normalization Service<br/>bioetl.domain.normalization_service]
        HASH[Hash Service<br/>bioetl.domain.transform.hash_service]
        TRANS[Transformers<br/>bioetl.domain.transform.transformers]
        SCHEMAS[Pandera Schemas<br/>bioetl.domain.schemas]
        MODELS[Domain Models<br/>bioetl.domain.models]
        REGISTRY[Provider Registry<br/>bioetl.domain.provider_registry]
    end

    subgraph "Infrastructure Layer"
        CLIENT[ChEMBL Client<br/>bioetl.infrastructure.clients.chembl]
        WRITER[Output Writer<br/>bioetl.infrastructure.output]
        LOGGER[Unified Logger<br/>bioetl.infrastructure.logging]
        CONFIG[Config Resolver<br/>bioetl.infrastructure.config]
        FILES[File Operations<br/>bioetl.infrastructure.files]
    end

    CLI --> ORCH
    REST --> ORCH
    MQ --> ORCH

    ORCH --> CONT
    CONT --> PBASE
    PBASE --> CPBASE
    CPBASE --> ENTITY

    PBASE --> EXTRACT
    PBASE --> VALID
    PBASE --> NORM
    PBASE --> HASH
    PBASE --> WRITER
    PBASE --> LOGGER
    PBASE --> HOOKS

    EXTRACT --> CLIENT
    VALID --> SCHEMAS
    NORM --> TRANS
    HASH --> TRANS

    CLIENT --> CONFIG
    WRITER --> FILES
    LOGGER --> CONFIG

    CONT --> REGISTRY
    REGISTRY --> CLIENT

    style CLI fill:#e8f5e9,stroke:#1b5e20
    style REST fill:#e8f5e9,stroke:#1b5e20
    style MQ fill:#e8f5e9,stroke:#1b5e20
    style ORCH fill:#fff3e0,stroke:#e65100
    style CONT fill:#fff3e0,stroke:#e65100
    style PBASE fill:#fff3e0,stroke:#e65100
    style VALID fill:#e1f5fe,stroke:#01579b
    style NORM fill:#e1f5fe,stroke:#01579b
    style HASH fill:#e1f5fe,stroke:#01579b
    style SCHEMAS fill:#e1f5fe,stroke:#01579b
    style CLIENT fill:#f3e5f5,stroke:#4a148c
    style WRITER fill:#f3e5f5,stroke:#4a148c
    style LOGGER fill:#f3e5f5,stroke:#4a148c
```

