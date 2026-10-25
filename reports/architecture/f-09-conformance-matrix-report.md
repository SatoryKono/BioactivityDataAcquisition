# Паспорт проверки F-09: conformance-матрица concrete adapter → port → production binding

## Метаданные проверки
- **Владелец работы**: Jules
- **Точная ревизия (SHA)**: `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
- **Область**: `src/bioetl/domain/ports`, `src/bioetl/infrastructure`, `src/bioetl/composition`, `tests/architecture/test_adapter_port_conformance.py`
- **Версии инструментов**: `ast` parser (Python 3)
- **Команды**: `python generate_report.py` (статический AST анализ абстрактных синтаксических деревьев)
- **Ожидаемый результат**: Полная матрица соответствия и отчёт о расхождениях между `production bindings` и `test_adapter_port_conformance.py`.
- **Допустимые пропуски**: Нет
- **Независимый проверяющий**: `[ОЖИДАЕТ НАЗНАЧЕНИЯ]`

## Правила включения (Inclusion Rules)
1. **Port**: Все классы в `src/bioetl` (преимущественно `src/bioetl/domain/ports`), имя которых оканчивается на `Port`.
2. **Concrete Adapter**: Классы в `src/bioetl/infrastructure`, которые:
   - Либо наследуются от `Port` (прямо или косвенно).
   - Либо инстанцируются в `src/bioetl/composition` в функциях, возвращающих `Port` (structural binding).
3. **Production Binding**: Подтверждение того, что адаптер инстанцируется и привязывается к порту в слое композиции (`src/bioetl/composition`).

## Количественные утверждения
- **MEASURED**: Найдено 93 портов.
- **MEASURED**: Найдено 7 связей (bindings), покрытых контрактными тестами `PORT_ADAPTER_CASES`.
- **MEASURED**: Найдено 25 уникальных портов, имеющих реализации в инфраструктуре.

## Матрица соответствия: Adapter -> Port -> Binding
| Port | Concrete Adapter | Origin | Test Coverage |
|------|------------------|--------|---------------|
| `AdrServicePort` | `FilesystemAdrCatalog` | `Inheritance` | FAIL |
| `ArtifactByteComparisonPort` | `FileArtifactByteComparisonAdapter` | `Inheritance` | FAIL |
| `AuditPort` | `FileAuditAdapter` | `Structural/Composition` | FAIL |
| `DQMonitorPort` | `DataQualityMonitor` | `Structural/Composition` | FAIL |
| `DQReportWriterPort` | `DQReportWriter` | `Structural/Composition` | FAIL |
| `DataSourcePort` | `BaseHttpAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `BaseSyncAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `ChemblAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `CrossRefAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `OpenAlexAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `PubChemAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `PubMedAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `SemanticScholarAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `UniProtAdapter` | `Inheritance` | FAIL |
| `DataSourcePort` | `UniProtIDMappingClient` | `Inheritance` | FAIL |
| `DeltaReaderPort` | `CompositeReplayInputReader` | `Inheritance` | FAIL |
| `ExportCatalogPort` | `ExportCatalogAdapter` | `Inheritance` | FAIL |
| `ExportWriterPort` | `ExportWriterAdapter` | `Inheritance` | FAIL |
| `ForeignKeyReconciliationPort` | `SilverForeignKeyReconciliationAdapter` | `Inheritance` | FAIL |
| `HealthMonitorPort` | `PersistingProviderHealthMonitor` | `Structural/Composition` | FAIL |
| `LineageStorePort` | `FileLineageStore` | `Inheritance` | FAIL |
| `LockPort` | `MemoryLock` | `Inheritance` | FAIL |
| `LoggerPort` | `NoOpLogger` | `Structural/Composition` | PASS |
| `LoggerPort` | `UnifiedLogger` | `Structural/Composition` | PASS |
| `MetricsPort` | `PrometheusMetrics` | `Inheritance` | FAIL |
| `MetricsPort` | `PrometheusMetrics` | `Structural/Composition` | FAIL |
| `ProteinClassificationPort` | `ChEMBLProteinClassificationGraph` | `Inheritance` | FAIL |
| `PublicationVocabularyPort` | `PublicationControlledVocabularyLoader` | `Inheritance` | FAIL |
| `RowReconciliationPort` | `StorageRowReconciliationAdapter` | `Inheritance` | FAIL |
| `RunLedgerPort` | `FileRunLedgerStore` | `Inheritance` | FAIL |
| `RunManifestPort` | `FileRunManifestStore` | `Inheritance` | FAIL |
| `RunReportStorePort` | `FileRunReportStoreAdapter` | `Structural/Composition` | FAIL |
| `WorkflowExecutionStatePort` | `FileWorkflowExecutionStateStore` | `Inheritance` | FAIL |
| `WorkflowLedgerPort` | `FileWorkflowLedgerStore` | `Inheritance` | FAIL |
| `WorkflowManifestPort` | `FileWorkflowManifestStore` | `Inheritance` | FAIL |

## Отчёт о расхождениях (Discrepancies)
- **ESTIMATED**: Около 33 production bindings НЕ покрыты в `PORT_ADAPTER_CASES`.
- Примеры отсутствующих связей:
  - Упущенный binding: `FilesystemAdrCatalog` -> `AdrServicePort` (Inheritance)
  - Упущенный binding: `FileArtifactByteComparisonAdapter` -> `ArtifactByteComparisonPort` (Inheritance)
  - Упущенный binding: `FileAuditAdapter` -> `AuditPort` (Structural/Composition)
  - Упущенный binding: `DataQualityMonitor` -> `DQMonitorPort` (Structural/Composition)
  - Упущенный binding: `DQReportWriter` -> `DQReportWriterPort` (Structural/Composition)
  - Упущенный binding: `BaseHttpAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `BaseSyncAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `ChemblAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `CrossRefAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `OpenAlexAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `PubChemAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `PubMedAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `SemanticScholarAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `UniProtAdapter` -> `DataSourcePort` (Inheritance)
  - Упущенный binding: `UniProtIDMappingClient` -> `DataSourcePort` (Inheritance)
  - ... и ещё 18 связей.

## Результат
**BLOCKER**: Недоступность поведенческих контрактных тестов для всех выявленных production bindings. Текущий conformance-набор (`test_adapter_port_conformance.py`) не полон. Расширение набора не производилось согласно требованиям режима ПРОВЕРКИ (код не менять).