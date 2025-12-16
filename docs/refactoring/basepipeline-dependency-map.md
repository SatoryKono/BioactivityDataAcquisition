# BasePipeline Dependency Map

**Generated:** 2025-12-16
**Updated:** 2025-12-16 (post-refactoring)
**Status:** Рефакторинг завершён

## 1. Current State (After Refactoring)

### 1.1 New Constructor Signature (3 parameters)

```python
def __init__(
    self,
    config: PipelineConfig,      # Immutable config
    runtime: PipelineRuntimeConfig,  # Runtime params
    services: PipelineServices,  # I/O ports with aclose()
) -> None
```

**Decomposition:**
| Structure | Fields | Frozen |
|-----------|--------|--------|
| `PipelineConfig` | `pipeline_name`, `provider`, `entity_type`, `primary_keys`, `silver_table`, `gold_table`, `batch_size`, `checkpoint_interval` | Yes |
| `PipelineRuntimeConfig` | `run_type`, `resume`, `limit` | Yes |
| `PipelineServices` | `data_source`, `storage`, `lock`, `checkpoint`, `quarantine`, `metrics`, `logger` + `aclose()` | Yes |

### 1.2 Internal Components (Lazy-Initialized)

```python
# All components created via from_components() - NO circular refs
self._orchestrator: PipelineOrchestrator | None = None
self._executor: PipelineExecutor | None = None
self._checkpoint_manager: CheckpointManager | None = None
self._quarantine_manager: QuarantineManager | None = None
self._error_classifier: ErrorClassifier | None = None
```

### 1.3 Circular Dependencies - RESOLVED

```
BEFORE (circular):
BasePipeline ─────creates────► PipelineOrchestrator
     ▲                               │
     └───────────references──────────┘

AFTER (no circular refs):
BasePipeline ─────creates────► PipelineOrchestrator.from_components(
     │                              config=...,
     │                              runtime=...,
     │                              executor=...,  # injected
     │                          )
     │
     └─── NO back-reference ───────────────────────────────────────►
```

## 2. File Dependencies (Updated)

### 2.1 New Files Created

| File | Purpose |
|------|---------|
| `application/core/pipeline_config.py` | `PipelineConfig`, `PipelineRuntimeConfig` |
| `application/core/pipeline_services.py` | `PipelineServices` with `aclose()` |
| `application/core/shutdown.py` | `ShutdownSignal` for graceful shutdown |

### 2.2 Direct Imports from `bioetl.application.core.base`

| File | Import | Usage |
|------|--------|-------|
| `cli.py` | `run_pipeline_flow` | CLI entry point (calls `aclose()`) |
| `orchestration/tasks.py` | `BasePipeline` (TYPE_CHECKING) | Prefect task type hint |
| `application/pipelines/chembl_activity.py` | `BasePipeline` | Inheritance |
| `application/core/__init__.py` | `BasePipeline` | Re-export |
| `application/core/orchestrator.py` | `BasePipeline` (TYPE_CHECKING) | Type hints only |
| `application/core/executor.py` | `BasePipeline` (TYPE_CHECKING) | Type hints only |

### 2.3 Test Dependencies (Updated)

| File | Fixture Pattern |
|------|-----------------|
| `tests/unit/application/test_base_pipeline.py` | `PipelineConfig` + `PipelineRuntimeConfig` + `PipelineServices` |
| `tests/unit/application/test_pipeline_executor.py` | Same + `from_components()` tests |
| `tests/unit/application/pipelines/test_chembl_activity.py` | `ChEMBLActivityPipeline.create()` |

## 3. Dependency Graph (After Refactoring)

```
                              cli.py
                                │
                                ▼
                        run_pipeline_flow()
                                │
                                ├─── try: await pipeline.run()
                                │
                                └─── finally: await pipeline.services.aclose()
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BasePipeline                                 │
│  ┌────────────────┐ ┌──────────────────┐ ┌────────────────────────┐ │
│  │ PipelineConfig │ │PipelineRuntime   │ │   PipelineServices     │ │
│  │   (frozen)     │ │   Config         │ │     (frozen)           │ │
│  └────────────────┘ └──────────────────┘ └────────────────────────┘ │
│                                                      │               │
│                                                      ▼               │
│                                              aclose() ───────────────┼──► Close all I/O
│                                                                      │
│         Lazy properties (no circular refs):                          │
│         ┌──────────────────────────────────────────────────────┐    │
│         │ @property orchestrator → Orchestrator.from_components │    │
│         │ @property executor → Executor.from_components         │    │
│         │ @property checkpoint_manager → CheckpointManager      │    │
│         └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ChEMBLActivityPipeline
                    ├── CHEMBL_ACTIVITY_CONFIG (default)
                    └── create(runtime, services) factory
```

## 4. Problems - ALL RESOLVED

### 4.1 God Object Anti-pattern ✅
- **Before:** 13 constructor parameters
- **After:** 3 structured parameters

### 4.2 Circular Dependencies ✅
- **Before:** Managers stored `self` reference
- **After:** `from_components()` injection, no back-refs

### 4.3 Violation of Single Responsibility ✅
- **Before:** Config + Orchestration mixed
- **After:** Config in dataclasses, behavior in pipeline

### 4.4 Resource Leaks ✅
- **Before:** No centralized cleanup
- **After:** `PipelineServices.aclose()` in `finally` block

## 5. Migration Guide

### For New Pipelines

```python
from bioetl.application.core import (
    BasePipeline,
    PipelineConfig,
    PipelineRuntimeConfig,
    PipelineServices,
)

# 1. Define config
MY_CONFIG = PipelineConfig(
    pipeline_name="my_pipeline",
    provider="my_provider",
    entity_type="my_entity",
    primary_keys=["entity_id"],
    silver_table="my_provider.my_entity",
)

# 2. Create pipeline class
class MyPipeline(BasePipeline):
    @classmethod
    def create(cls, runtime: PipelineRuntimeConfig, services: PipelineServices):
        return cls(MY_CONFIG, runtime, services)

    async def transform_bronze_to_silver(self, context, record):
        # Transform logic
        return record
```

### For Tests

```python
@pytest.fixture
def pipeline():
    config = PipelineConfig(...)
    runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)

    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        logger=mock_logger,
    )
    return ConcretePipeline(config, runtime, services)
```

## 6. Deprecation Timeline

| Date | Action |
|------|--------|
| 2025-12-16 | `from_params()` deprecated with warning |
| 2025-01-15 | `from_params()` removed |
