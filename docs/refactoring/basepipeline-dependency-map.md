# BasePipeline Dependency Map

**Generated:** 2025-12-16
**Purpose:** Map all dependencies before refactoring BasePipeline (God Object)

## 1. Current State Analysis

### 1.1 Constructor Parameters (13 dependencies - God Object)

```python
def __init__(
    self,
    pipeline_name: str,          # Config
    provider: str,               # Config
    entity_type: str,            # Config
    run_type: RunType,           # Runtime
    data_source: DataSourcePort, # Port
    storage: StoragePort,        # Port
    lock: LockPort,              # Port
    checkpoint: CheckpointPort,  # Port
    quarantine: QuarantinePort,  # Port
    logger: BoundLogger,         # Infrastructure
    metrics: MetricsPort,        # Port
    resume: bool = False,        # Runtime
    limit: int | None = None,    # Runtime
) -> None
```

**Categorization:**
| Category | Parameters | Count |
|----------|------------|-------|
| Config (static) | `pipeline_name`, `provider`, `entity_type` | 3 |
| Runtime (dynamic) | `run_type`, `resume`, `limit` | 3 |
| Ports (I/O) | `data_source`, `storage`, `lock`, `checkpoint`, `quarantine`, `metrics` | 6 |
| Infrastructure | `logger` | 1 |
| **Total** | | **13** |

### 1.2 Internal Components Created

```python
self.context = PipelineContext(...)
self.orchestrator = PipelineOrchestrator(self)    # Circular ref!
self.executor = PipelineExecutor(self)            # Circular ref!
self.lock_manager = LockManager(self)             # Circular ref!
self.checkpoint_manager = CheckpointManager(...)
self.error_classifier = ErrorClassifier()
self.quarantine_manager = QuarantineManager(self) # Circular ref!
```

### 1.3 Circular Dependencies

```
BasePipeline ─────creates────► PipelineOrchestrator
     ▲                               │
     └───────────references──────────┘

BasePipeline ─────creates────► PipelineExecutor
     ▲                               │
     └───────────references──────────┘

BasePipeline ─────creates────► LockManager
     ▲                               │
     └───────────references──────────┘

BasePipeline ─────creates────► QuarantineManager
     ▲                               │
     └───────────references──────────┘
```

## 2. File Dependencies

### 2.1 Direct Imports from `bioetl.application.core.base`

| File | Import | Usage |
|------|--------|-------|
| `cli.py:19` | `run_pipeline_flow` | CLI entry point |
| `orchestration/tasks.py:18` | `BasePipeline` (TYPE_CHECKING) | Prefect task type hint |
| `application/pipelines/chembl_activity.py:15` | `BasePipeline` | Inheritance |
| `application/core/__init__.py:3` | `BasePipeline` | Re-export |
| `application/core/orchestrator.py:18` | `BasePipeline` (TYPE_CHECKING) | Constructor param |
| `application/core/executor.py:19` | `BasePipeline` (TYPE_CHECKING) | Constructor param |
| `application/core/lock_manager.py:11` | `BasePipeline` (TYPE_CHECKING) | Constructor param |
| `application/core/quarantine_manager.py:8` | `BasePipeline` (TYPE_CHECKING) | Constructor param |

### 2.2 Test Dependencies

| File | Usage |
|------|-------|
| `tests/unit/application/test_base_pipeline.py` | Direct tests for BasePipeline |
| `tests/unit/application/test_pipeline_executor.py` | ConcretePipeline(BasePipeline) mock |

### 2.3 Re-exports

| File | Exports |
|------|---------|
| `application/core/__init__.py` | `BasePipeline` in `__all__` |

## 3. Dependency Graph

```
                              cli.py
                                │
                                ▼
                        run_pipeline_flow()
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      BasePipeline                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Config: pipeline_name, provider, entity_type        │   │
│  │ Runtime: run_type, resume, limit, run_id            │   │
│  │ Ports: data_source, storage, lock, checkpoint,      │   │
│  │        quarantine, metrics                          │   │
│  │ Infra: logger, context                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│            ┌──────────────┼──────────────┐                 │
│            ▼              ▼              ▼                 │
│     Orchestrator      Executor      LockManager            │
│            │              │              │                 │
│            └──────────────┴──────────────┘                 │
│                    (all reference `self`)                  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ChEMBLActivityPipeline (inherits)
```

## 4. Problems Identified

### 4.1 God Object Anti-pattern
- 13 constructor parameters
- Multiple responsibilities: config, runtime, I/O ports
- Hard to test in isolation

### 4.2 Circular Dependencies
- `BasePipeline` creates managers that reference back to it
- Tight coupling prevents independent evolution
- Makes mocking difficult

### 4.3 Violation of Single Responsibility
- Holds both configuration AND orchestration logic
- Mixes data (config) with behavior (managers)

## 5. Proposed Solution (ADR-0005)

### 5.1 Split into:
1. **PipelineConfig** (dataclass) - holds configuration
2. **PipelineServices** (dataclass) - holds port dependencies
3. **BasePipeline** (refactored) - behavior only, receives Config + Services

### 5.2 Migration Strategy
1. Create new structures with compatibility shim
2. Deprecate old constructor
3. Migrate concrete pipelines
4. Remove shim after 14 days

## 6. Impact Assessment

| Component | Change Required | Risk |
|-----------|----------------|------|
| `ChEMBLActivityPipeline` | Update constructor | Medium |
| `cli.py` | Update pipeline creation | Low |
| `orchestration/tasks.py` | Update type hints | Low |
| Manager classes | Accept Config/Services instead | Medium |
| Tests | Update fixtures | Medium |
