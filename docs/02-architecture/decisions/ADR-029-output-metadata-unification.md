---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-029: Output Metadata Unification

**Date:** 2026-01-23
**Decision makers:** @BioETL-Team
**Relates to:** RULES.md §2.4 (Lineage Requirements), ADR-014 (Deterministic Writes)

## Context

Bronze/Silver/Gold Medallion layers использовали разные структуры для `output`-метаданных в sidecar-файлах:

| Layer | Класс | Поля |
|-------|-------|------|
| Bronze | `OutputMetadata` | `total_records`, `total_bytes`, `files`, `format`, `compression` |
| Silver | `SilverOutputMetadata` | `record_count`, `content_hash` |
| Gold | `GoldOutputMetadata` | `record_count`, `partition_count`, `total_bytes`, `format` |

### Проблемы

1. **Несогласованное именование**: `total_records` vs `record_count`
2. **Отсутствует общий контракт**: Усложняет downstream-аналитику и мониторинг
3. **Пропущенные поля**: `total_bytes` отсутствует в Silver
4. **Нет timestamps записи**: Отсутствуют `write_started_at`/`write_completed_at`
5. **Дублирование delta-version**: В Silver версии есть в `DeltaMetrics`, но не в output

## Decision

Унифицировать output-метаданные через паттерн **Base + Extension**:

### BaseOutputMetadata (Общий контракт)

```python
class BaseOutputMetadata(BaseModel):
    """Base output metadata contract for all Medallion layers."""

    model-config = ConfigDict(extra="forbid")

    record_count: int = Field(ge=0, description="Total records written")
    total_bytes: int = Field(ge=0, description="Total size in bytes")
    content_hash: str | None = Field(description="SHA256 hash for change detection")
    write_started_at: datetime | None = Field(description="Write start timestamp")
    write_completed_at: datetime | None = Field(description="Write completion timestamp")

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
    delta-version_before: int | None
    delta-version-after: int | None

class GoldOutputExt(BaseModel):
    partition_count: int = 0
    format: Literal["delta", "parquet"] = "delta"
```

### Layer Metadata Composition

```python
class BronzeMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output_ext: BronzeOutputExt         # Layer-specific

class SilverMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output_ext: SilverOutputExt         # Layer-specific

class GoldMetadata(BaseModel):
    output: BaseOutputMetadata          # Unified base
    output_ext: GoldOutputExt           # Layer-specific
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

    def __init__(self, **data: object) -> None:
        warnings.warn(
            "OutputMetadata is deprecated, use BaseOutputMetadata + BronzeOutputExt...",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)
```

## Consequences

### Positive

1. **Unified analytics**: Все слои экспортируют одинаковые базовые метрики
2. **Duration tracking**: `write-duration-ms` доступен через computed field
3. **Change detection**: `content_hash` доступен на всех слоях
4. **Monitoring consistency**: Prometheus/Grafana dashboards могут использовать единый набор метрик
5. **Type safety**: `extra="forbid"` предотвращает случайные поля

### Negative

1. **Breaking change**: Существующий код использующий `output.total_records` (Bronze) требует обновления
2. **Schema migration**: Существующие sidecar-файлы v1.0 не совместимы с v1.1

### Neutral

- Delta versions дублируются в Silver: `DeltaMetrics.version-*` и `SilverOutputExt.delta-version-*`
- Это осознанное решение для полноты output-контракта

## Implementation

### Files Modified

**Domain Models:**
- `src/bioetl/domain/models/metadata.py` — BaseOutputMetadata, *OutputExt классы

**DTOs:**
- `src/bioetl/domain/ports/metadata_coordinator.py` — Добавлены `version_before`, `total_bytes`, `partition_count`

**Services:**
- `src/bioetl/application/services/metadata_coordinator.py` — Обновлены create_*_metadata методы

**Infrastructure:**
- `src/bioetl/infrastructure/storage/bronze_writer.py` — _build_full_bronze_metadata
- `src/bioetl/infrastructure/storage/metadata_builder.py` — Silver/Gold builders

### JSON Output Format

**Before (v1.0):**
```json
{
  "output": {
    "total_records": 1000,
    "total_bytes": 50000,
    "files": [...]
  }
}
```

**After (v1.1):**
```json
{
  "output": {
    "record_count": 1000,
    "total_bytes": 50000,
    "content_hash": "sha256:...",
    "write_started_at": "2026-01-23T12:00:00Z",
    "write_completed_at": "2026-01-23T12:00:05Z"
  },
  "output_ext": {
    "files": [...],
    "format": "jsonl+zstd",
    "compression": "zstd"
  }
}
```

## Tests

### Unit Tests

- `tests/unit/domain/models/test_metadata_output.py` — BaseOutputMetadata, *OutputExt

### Architecture Tests

- `tests/architecture/test_metadata_output_contract.py` — Contract validation

## References

- RULES.md §2.4 — Lineage Requirements
- ADR-014 — Deterministic Writes (content hash)
- glossary.md — Ubiquitous Language definitions
