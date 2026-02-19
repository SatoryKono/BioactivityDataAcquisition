# ADR-029: Output Metadata Unification

**Status:** Accepted
**Date:** 2026-01-23
**Decision makers:** @BioETL-Team
**Relates to:** RULES.md §2.4 (Lineage Requirements), ADR-014 (Deterministic Writes)

## Context

Bronze/Silver/Gold Medallion layers использовали разные структуры для `output`-метаданных в sidecar-файлах:

| Layer | Класс | Поля |
|-------|-------|------|
| Bronze | `OutputMetadata` | `total-records`, `total-bytes`, `files`, `format`, `compression` |
| Silver | `SilverOutputMetadata` | `record-count`, `content-hash` |
| Gold | `GoldOutputMetadata` | `record-count`, `partition-count`, `total-bytes`, `format` |

### Проблемы

1. **Несогласованное именование**: `total-records` vs `record-count`
2. **Отсутствует общий контракт**: Усложняет downstream-аналитику и мониторинг
3. **Пропущенные поля**: `total-bytes` отсутствует в Silver
4. **Нет timestamps записи**: Отсутствуют `write-started-at`/`write-completed-at`
5. **Дублирование delta-version**: В Silver версии есть в `DeltaMetrics`, но не в output

## Decision

Унифицировать output-метаданные через паттерн **Base + Extension**:

### BaseOutputMetadata (Общий контракт)

```python
class BaseOutputMetadata(BaseModel):
    """Base output metadata contract for all Medallion layers."""

    model-config = ConfigDict(extra="forbid")

    record-count: int = Field(ge=0, description="Total records written")
    total-bytes: int = Field(ge=0, description="Total size in bytes")
    content-hash: str | None = Field(description="SHA256 hash for change detection")
    write-started-at: datetime | None = Field(description="Write start timestamp")
    write-completed-at: datetime | None = Field(description="Write completion timestamp")

    @computed-field
    @property
    def write-duration-ms(self) -> int | None:
        """Calculate write duration in milliseconds."""
```

### Layer-Specific Extensions

```python
class BronzeOutputExt(BaseModel):
    files: list[FileOutputMetadata]
    format: str = "jsonl+zstd"
    compression: str = "zstd"

class SilverOutputExt(BaseModel):
    delta-version-before: int | None
    delta-version-after: int | None

class GoldOutputExt(BaseModel):
    partition-count: int = 0
    format: Literal["delta", "parquet"] = "delta"
```

### Layer Metadata Composition

```python
class BronzeMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output-ext: BronzeOutputExt         # Layer-specific

class SilverMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output-ext: SilverOutputExt         # Layer-specific

class GoldMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output-ext: GoldOutputExt           # Layer-specific
```

### Metadata Schema Version Bump

Версия metadata schema увеличена с `1.0` до `1.1` для всех слоёв.

### Backward Compatibility

Старые классы (`OutputMetadata`, `SilverOutputMetadata`, `GoldOutputMetadata`) сохранены как deprecated:

```python
class OutputMetadata(BaseModel):
    """Bronze output information (DEPRECATED).

    .. deprecated:: 5.10.0
        Use BaseOutputMetadata + BronzeOutputExt composition instead.
        Will be removed in v6.0.
    """

    def --init--(self, **data: object) -> None:
        warnings.warn(
            "OutputMetadata is deprecated, use BaseOutputMetadata + BronzeOutputExt...",
            DeprecationWarning,
            stacklevel=2,
        )
        super().--init--(**data)
```

## Consequences

### Positive

1. **Unified analytics**: Все слои экспортируют одинаковые базовые метрики
2. **Duration tracking**: `write-duration-ms` доступен через computed field
3. **Change detection**: `content-hash` доступен на всех слоях
4. **Monitoring consistency**: Prometheus/Grafana dashboards могут использовать единый набор метрик
5. **Type safety**: `extra="forbid"` предотвращает случайные поля

### Negative

1. **Breaking change**: Существующий код использующий `output.total-records` (Bronze) требует обновления
2. **Schema migration**: Существующие sidecar-файлы v1.0 не совместимы с v1.1

### Neutral

- Delta versions дублируются в Silver: `DeltaMetrics.version-*` и `SilverOutputExt.delta-version-*`
- Это осознанное решение для полноты output-контракта

## Implementation

### Files Modified

**Domain Models:**
- `src/bioetl/domain/models/metadata.py` — BaseOutputMetadata, *OutputExt классы

**DTOs:**
- `src/bioetl/domain/ports/metadata-coordinator.py` — Добавлены `version-before`, `total-bytes`, `partition-count`

**Services:**
- `src/bioetl/composition/services/metadata-coordinator.py` — Обновлены create-*-metadata методы

**Infrastructure:**
- `src/bioetl/infrastructure/storage/bronze-writer.py` — -build-full-bronze-metadata
- `src/bioetl/infrastructure/storage/metadata-builder.py` — Silver/Gold builders

### JSON Output Format

**Before (v1.0):**
```json
{
  "output": {
    "total-records": 1000,
    "total-bytes": 50000,
    "files": [...]
  }
}
```

**After (v1.1):**
```json
{
  "output": {
    "record-count": 1000,
    "total-bytes": 50000,
    "content-hash": "sha256:...",
    "write-started-at": "2026-01-23T12:00:00Z",
    "write-completed-at": "2026-01-23T12:00:05Z"
  },
  "output-ext": {
    "files": [...],
    "format": "jsonl+zstd",
    "compression": "zstd"
  }
}
```

## Tests

### Unit Tests

- `tests/unit/domain/models/test-metadata-output.py` — BaseOutputMetadata, *OutputExt

### Architecture Tests

- `tests/architecture/test-metadata-output-contract.py` — Contract validation

## References

- RULES.md §2.4 — Lineage Requirements
- ADR-014 — Deterministic Writes (content hash)
- glossary.md — Ubiquitous Language definitions
