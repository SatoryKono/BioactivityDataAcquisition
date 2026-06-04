# Domain Control Plane Artifacts

## Обзор

Domain Control Plane Artifacts обеспечивают immutable provenance tracking и reproducibility для выполнения пайплайнов. Эти domain models представляют собой control-plane контракты для orchestrating pipeline и workflow executions с полной отслеживаемостью происхождения данных (provenance).

**Связанные ADR:**
- ADR-044 (Workflow Control Plane)
- ADR-047 (Control Plane Architecture)

## Архитектура

### Основные компоненты

```
src/bioetl/domain/control_plane/
├── __init__.py                              # Публичный API
├── artifact_lifecycle.py                    # Lifecycle artifacts
├── effective_config_artifact.py             # Effective config artifacts
├── effective_config_environment.py          # Execution environment
├── config_source_hashing.py                 # Config source hashing
├── contract_registry.py                     # Contract registry
├── contract_registry_helpers.py             # Registry helpers
├── contract_registry_service.py             # Registry service
├── contract_registry_types.py               # Registry types
├── gold_contract.py                         # Gold contracts
├── run_manifest.py                          # Run manifest
├── run_ledger.py                            # Run ledger
├── run_ledger_replay.py                     # Replay projection
├── _run_manifest_serialization.py           # Manifest serialization
├── _run_ledger_serialization.py             # Ledger serialization
├── _run_ledger_runtime.py                   # Runtime ledger
├── _run_ledger_event_family.py              # Event family
├── _run_ledger_replay_policy.py             # Replay policy
├── workflow_manifest.py                     # Workflow manifest
├── workflow_ledger.py                       # Workflow ledger
├── workflow_execution_state.py              # Workflow execution state
├── reproducibility_policy.py                # Reproducibility policy
├── reproducibility_profiles.py               # Reproducibility profiles
└── ledger/                                  # Ledger core events
    └── core_events.py
```

## Ключевые сущности

### 1. RunManifest

**Файл:** `run_manifest.py`

**Назначение:** Immutable provenance/control-plane artifact для одного запущенного run.

**Ключевые поля:**
- `manifest_id: str` - уникальный идентификатор manifest
- `execution_fingerprint: str` - fingerprint выполнения
- `schema_version: str` - версия схемы
- `created_at: datetime` - время создания (UTC)
- `run_id: RunID` - идентификатор run
- `run_type: RunType` - тип run (INCREMENTAL/FULL/REPLAY)
- `pipeline_name: str` - имя пайплайна
- `provider: str` - провайдер данных
- `entity: str` - сущность данных
- `launch_context: dict[str, object]` - контекст запуска
- `runtime_config: dict[str, object]` - runtime конфигурация
- `resolved_config: dict[str, object]` - резолвенная конфигурация
- `code_provenance: RunCodeProvenance` - provenance кода
- `replay_of_run_id: str | None` - ID replayed run
- `replay_of_manifest_id: str | None` - ID replayed manifest
- `replay_capability: ReplayCapability` - capability replay
- `source_refs: tuple[RunSourceRef, ...]` - ссылки на источники
- `planned_artifacts: tuple[RunArtifactRef, ...]` - планируемые артефакты

**Invariants:**
- `manifest_id`, `execution_fingerprint`, `schema_version`, `pipeline_name`, `provider`, `entity` должны быть non-empty strings
- `created_at` нормализуется к UTC
- Все dict поля frozen (неизменяемы)

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

### 2. RunCodeProvenance

**Файл:** `run_manifest.py`

**Назначение:** Code/config provenance fields для reproducibility.

**Поля:**
- `pipeline_version: str | None` - версия пайплайна
- `git_commit: str | None` - git commit hash
- `source_revision_state: str | None` - состояние source revision (clean/dirty)
- `dependency_lock_hash: str | None` - hash dependency lock файла
- `config_hash: str | None` - hash конфигурации
- `resolved_config_hash: str | None` - hash резолвенной конфигурации
- `effective_config_hash: str | None` - hash effective конфигурации
- `source_fingerprint: str | None` - fingerprint источника
- `contract_ref: str | None` - ссылка на контракт
- `contract_version: str | None` - версия контракта
- `contract_schema_hash: str | None` - hash схемы контракта
- `dq_policy_ref: str | None` - ссылка на DQ policy
- `rule_bundle_version: str | None` - версия rule bundle
- `normalization_profile_ref: str | None` - ссылка на normalization profile
- `normalization_profile_version: str | None` - версия normalization profile
- `normalization_profile_hash: str | None` - hash normalization profile
- `dq_contract_compatibility_hash: str | None` - hash DQ contract compatibility
- `effective_config_artifact_id: str | None` - ID effective config artifact

### 3. ReplayCapability

**Файл:** `run_manifest.py`

**Назначение:** Классификация exact-replay capability для manifested run.

**Значения:**
- `EXACT_REPLAY_SUPPORTED` - поддерживается точный replay
- `RESUME_ONLY` - только resume возможен
- `REBUILD_ONLY` - только rebuild возможен

### 4. RunSourceRef

**Файл:** `run_manifest.py`

**Назначение:** Каноническая ссылка на источник, захваченная в manifest.

**Поля:**
- `provider: str` - провайдер данных
- `entity: str` - сущность данных
- `pipeline_name: str` - имя пайплайна
- `query: str | None` - query (если применимо)
- `input_snapshots: tuple[RunInputSnapshotRef, ...]` - snapshots входных данных

### 5. RunInputSnapshotRef

**Файл:** `run_manifest.py`

**Назначение:** Immutable snapshot reference для одного external input batch.

**Поля:**
- `snapshot_id: str` - идентификатор snapshot
- `content_hash: str` - hash содержимого
- `immutable_uri: str | None` - immutable URI
- `query_fingerprint: str | None` - fingerprint query
- `storage_provider: str | None` - провайдер хранения
- `object_bucket: str | None` - bucket объекта
- `object_key: str | None` - ключ объекта
- `object_version_id: str | None` - версия объекта
- `etag: str | None` - ETag объекта
- `last_modified: str | None` - время последней модификации
- `captured_at: datetime | None` - время захвата

### 6. RunArtifactRef

**Файл:** `run_manifest.py`

**Назначение:** Планируемая локация артефакта, захваченная в manifest.

**Поля:**
- `layer: str` - слой (bronze/silver/gold)
- `path: str` - путь к артефакту

### 7. RunLedgerEntry

**Файл:** `_run_ledger_runtime.py`

**Назначение:** Append-only control-plane event для одного pipeline execution.

**Ключевые поля:**
- `entry_id: str` - идентификатор записи
- `manifest_id: str` - идентификатор manifest
- `run_id: RunID` - идентификатор run
- `event_type: str` - тип события
- `occurred_at: datetime` - время события
- `stage_name: str | None` - имя этапа
- `status: str | None` - статус
- `message: str | None` - сообщение
- `error_type: str | None` - тип ошибки
- `details: dict[str, object] | None` - детали

**Типы событий:**
- `MANIFEST_CREATED_EVENT` - manifest создан
- `RUN_STARTED_EVENT` - run запущен
- `RUN_FINISHED_EVENT` - run завершен
- `RUN_FAILED_EVENT` - run failed
- `RUN_SHUTDOWN_EVENT` - run shutdown
- `STAGE_STARTED_EVENT` - этап запущен
- `STAGE_COMPLETED_EVENT` - этап завершен
- `ARTIFACT_PUBLISHED_EVENT` - артефакт опубликован
- `INPUT_SNAPSHOT_PUBLISHED_EVENT` - input snapshot опубликован
- `DQ_POLICY_APPLIED_EVENT` - DQ policy применена
- Composite-specific события:
  - `COMPOSITE_DEPENDENCY_COMPLETED_EVENT`
  - `COMPOSITE_ENRICHER_COMPLETED_EVENT`
  - `COMPOSITE_MERGE_COMPLETED_EVENT`

### 8. WorkflowManifest

**Файл:** `workflow_manifest.py`

**Назначение:** Immutable workflow execution-intent artifact.

**Ключевые поля:**
- `manifest_id: str` - идентификатор manifest
- `workflow_run_id: RunID` - идентификатор workflow run
- `execution_fingerprint: str` - fingerprint выполнения
- `schema_version: str` - версия схемы
- `created_at: datetime` - время создания
- `workflow_name: str` - имя workflow
- `workflow_version: str` - версия workflow
- `launch_context: dict[str, object]` - контекст запуска
- `defaults: dict[str, object]` - значения по умолчанию
- `selected_step_ids: tuple[str, ...]` - выбранные шаги
- `steps: tuple[WorkflowManifestStep, ...]` - шаги workflow
- `resumed_from_manifest_id: str | None` - ID resumed manifest

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

### 9. WorkflowManifestStep

**Файл:** `workflow_manifest.py`

**Назначение:** Immutable описание одного resolved workflow step.

**Поля:**
- `step_id: str` - идентификатор шага
- `kind: str` - тип шага
- `depends_on: tuple[str, ...]` - зависимости
- `pipeline_name: str | None` - имя пайплайна
- `transform_name: str | None` - имя transform
- `run_options: dict[str, object] | None` - опции запуска
- `config: dict[str, object] | None` - конфигурация

**Методы:**
- `to_dict()` - сериализация в JSON
- `from_dict()` - десериализация из JSON

### 10. WorkflowLedgerEntry

**Файл:** `workflow_ledger.py`

**Назначение:** Append-only control-plane event для одного workflow execution.

**Ключевые поля:**
- `entry_id: str` - идентификатор записи
- `manifest_id: str` - идентификатор manifest
- `workflow_run_id: RunID` - идентификатор workflow run
- `event_type: str` - тип события
- `occurred_at: datetime` - время события
- `event_family: str | None` - семейство события (workflow/step/operator)
- `status: str | None` - статус
- `step_id: str | None` - идентификатор шага
- `step_kind: str | None` - тип шага
- `message: str | None` - сообщение
- `error_type: str | None` - тип ошибки
- `idempotency_key: str | None` - ключ идемпотентности
- `details: dict[str, object] | None` - детали

**Типы событий:**
- `WORKFLOW_MANIFEST_CREATED_EVENT` - workflow manifest создан
- `WORKFLOW_STARTED_EVENT` - workflow запущен
- `WORKFLOW_RESUMED_EVENT` - workflow возобновлен
- `WORKFLOW_FINISHED_EVENT` - workflow завершен
- `WORKFLOW_FAILED_EVENT` - workflow failed
- `STEP_STARTED_EVENT` - шаг запущен
- `STEP_COMPLETED_EVENT` - шаг завершен
- `STEP_COMMIT_PENDING_CONFIRMATION_EVENT` - шаг ожидает подтверждения commit
- `WORKFLOW_REPAIR_REQUESTED_EVENT` - запрос на repair
- `WORKFLOW_FORCE_REQUESTED_EVENT` - запрос на force

### 11. ReproducibilityPolicy

**Файл:** `reproducibility_policy.py`

**Назначение:** Assessment reproducibility policy для determinism и replay readiness.

**Ключевые функции:**
- `assess_reproducibility_policy()` - оценка reproducibility policy
- `resolve_replay_capability()` - резолвинг replay capability
- `resolve_replay_readiness_verdict()` - резолвинг replay readiness verdict
- `build_snapshot_envelope_status()` - построение snapshot envelope status
- `normalize_required_persistence_profile()` - нормализация persistence profile

**Вердикты:**
- `REPLAY_READY` - готов к replay
- `REPLAY_NOT_READY` - не готов к replay
- `REPLAY_PARTIALLY_READY` - частично готов к replay

### 12. EffectiveConfigArtifact

**Файл:** `effective_config_artifact.py`

**Назначение:** Effective config artifact для resolved configuration.

**Ключевые поля:**
- `artifact_id: str` - идентификатор artifact
- `config_hash: str` - hash конфигурации
- `resolved_config: ResolvedConfigSnapshot` - резолвенная конфигурация
- `execution_config: EffectiveExecutionConfig` - execution конфигурация
- `dq_policy: DQPolicySnapshot` - DQ policy snapshot
- `environment_snapshot: ExecutionEnvironmentSnapshot` - snapshot environment
- `source_provenance: SourceClassProvenance` - provenance источника

### 13. ControlPlaneArtifactLifecycle

**Файл:** `artifact_lifecycle.py`

**Назначение:** Lifecycle policy для control-plane artifacts.

**Ключевые классы:**
- `ControlPlaneArtifactLifecyclePolicy` - политика lifecycle
- `ControlPlaneArtifactLifecyclePlan` - план lifecycle
- `ControlPlaneArtifactLifecycleDecision` - решение lifecycle
- `ControlPlaneArtifactLifecycleApplyResult` - результат применения
- `ControlPlaneArtifactRef` - ссылка на artifact
- `ControlPlaneArtifactSurface` - поверхность artifact
- `ControlPlaneArtifactReplayImpact` - влияние на replay

## Workflow

### Run Lifecycle

1. **Manifest Creation**
   - Создание `RunManifest` с provenance информацией
   - Захват `RunCodeProvenance`
   - Определение `ReplayCapability`
   - Захват `RunSourceRef` и `RunInputSnapshotRef`

2. **Ledger Recording**
   - Запись `RunLedgerEntry` событий в append-only ledger
   - Event types: `MANIFEST_CREATED`, `RUN_STARTED`, `STAGE_STARTED`, `STAGE_COMPLETED`, `ARTIFACT_PUBLISHED`, `RUN_FINISHED`/`RUN_FAILED`

3. **Replay Assessment**
   - Оценка `ReproducibilityPolicy`
   - Резолвинг `ReplayReadinessVerdict`
   - Определение `ReplayCapability`

### Workflow Lifecycle

1. **Workflow Manifest Creation**
   - Создание `WorkflowManifest` с шагами
   - Определение зависимостей между шагами
   - Захват launch context

2. **Workflow Ledger Recording**
   - Запись `WorkflowLedgerEntry` событий
   - Event types: `WORKFLOW_MANIFEST_CREATED`, `WORKFLOW_STARTED`, `STEP_STARTED`, `STEP_COMPLETED`, `WORKFLOW_FINISHED`/`WORKFLOW_FAILED`

3. **Step Execution**
   - Выполнение шагов согласно зависимостям
   - Запись step-specific событий
   - Обработка operator requests (repair/force)

## Связанные ADR

- **ADR-044:** Workflow Control Plane - архитектура workflow control plane
- **ADR-047:** Control Plane Architecture - детальная архитектура control plane

## Зависимости

### Internal
- `bioetl.domain.types` - domain types (RunID, RunType)
- `bioetl.domain.ports` - порты для persistence

### External
- `dataclasses` - для dataclass моделей
- `datetime` - для timestamps
- `uuid` - для UUID генерации
- `enum` - для enum типов

## Примеры использования

### Создание RunManifest

```python
from bioetl.domain.control_plane import (
    RunManifest,
    RunCodeProvenance,
    RunSourceRef,
    ReplayCapability,
)
from bioetl.domain.types import RunID, RunType
from datetime import datetime, UTC
from uuid import uuid4

code_provenance = RunCodeProvenance(
    pipeline_version="1.0.0",
    git_commit="abc123",
    source_revision_state="clean",
    dependency_lock_hash="hash123",
    config_hash="config456",
)

source_ref = RunSourceRef(
    provider="pubchem",
    entity="bioactivity",
    pipeline_name="pubchem_pipeline",
)

manifest = RunManifest(
    manifest_id="manifest-001",
    execution_fingerprint="fingerprint-001",
    schema_version="1.0",
    created_at=datetime.now(UTC),
    run_id=RunID(uuid4()),
    run_type=RunType.INCREMENTAL,
    pipeline_name="pubchem_pipeline",
    provider="pubchem",
    entity="bioactivity",
    code_provenance=code_provenance,
    replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    source_refs=(source_ref,),
)
```

### Создание WorkflowManifest

```python
from bioetl.domain.control_plane import (
    WorkflowManifest,
    WorkflowManifestStep,
)
from bioetl.domain.types import RunID
from datetime import datetime, UTC
from uuid import uuid4

step1 = WorkflowManifestStep(
    step_id="step-001",
    kind="pipeline",
    depends_on=(),
    pipeline_name="pubchem_pipeline",
)

step2 = WorkflowManifestStep(
    step_id="step-002",
    kind="pipeline",
    depends_on=("step-001",),
    pipeline_name="chembl_pipeline",
)

workflow_manifest = WorkflowManifest(
    manifest_id="workflow-manifest-001",
    workflow_run_id=RunID(uuid4()),
    execution_fingerprint="workflow-fingerprint-001",
    schema_version="1.0",
    created_at=datetime.now(UTC),
    workflow_name="bioactivity_workflow",
    workflow_version="1.0.0",
    launch_context={"trigger": "manual"},
    defaults={"timeout": 3600},
    selected_step_ids=("step-001", "step-002"),
    steps=(step1, step2),
)
```

## Тестирование

Тесты для control plane artifacts находятся в:
- `tests/unit/domain/control_plane/` - unit тесты
- `tests/integration/domain/control_plane/` - integration тесты

## Метрики качества

- Покрытие тестами: >90%
- Cyclomatic complexity: <10 для всех функций
- Type coverage: 100% (strict mode)
- Immutability: все key artifacts frozen (dataclass frozen=True)