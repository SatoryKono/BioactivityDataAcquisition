______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-029: Output Metadata Unification

**Date:** 2026-01-23
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Bronze/Silver/Gold Medallion layers использовали разные структуры для `output`-метаданных в sidecar-файлах:

| Layer  | Класс                  | Поля                                                             |
| ------ | ---------------------- | ---------------------------------------------------------------- |
| Bronze | `OutputMetadata`       | `total_records`, `total_bytes`, `files`, `format`, `compression` |
| Silver | `SilverOutputMetadata` | `record_count`, `content_hash`                                   |
| Gold   | `GoldOutputMetadata`   | `record_count`, `partition_count`, `total_bytes`, `format`       |

### Проблемы

1. **Несогласованное именование**: `total_records` vs `record_count`
1. **Отсутствует общий контракт**: Усложняет downstream-аналитику и мониторинг
1. **Пропущенные поля**: `total_bytes` отсутствует в Silver
1. **Нет timestamps записи**: Отсутствуют `write_started_at`/`write_completed_at`
1. **Дублирование delta-version**: В Silver версии есть в `DeltaMetrics`, но не в output

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
    delta - version_before: int | None
    delta - version - after: int | None


class GoldOutputExt(BaseModel):
    partition_count: int = 0
    format: Literal["delta", "parquet"] = "delta"
```

### Layer Metadata Composition

```python
class BronzeMetadata(BaseModel):
    output: BaseOutputMetadata  # Unified base
    output_ext: BronzeOutputExt  # Layer-specific


class SilverMetadata(BaseModel):
    output: BaseOutputMetadata  # Unified base
    output_ext: SilverOutputExt  # Layer-specific


class GoldMetadata(BaseModel):
    output: BaseOutputMetadata  # Unified base
    output_ext: GoldOutputExt  # Layer-specific
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
1. **Duration tracking**: `write-duration-ms` доступен через computed field
1. **Change detection**: `content_hash` доступен на всех слоях
1. **Monitoring consistency**: Prometheus/Grafana dashboards могут использовать единый набор метрик
1. **Type safety**: `extra="forbid"` предотвращает случайные поля

### Negative

1. **Breaking change**: Существующий код использующий `output.total_records` (Bronze) требует обновления
1. **Schema migration**: Существующие sidecar-файлы v1.0 не совместимы с v1.1

### Neutral

- Delta versions дублируются в Silver: `DeltaMetrics.version-*` и `SilverOutputExt.delta-version-*`
- Это осознанное решение для полноты output-контракта

## Implementation

### Files Modified

**Domain Models:**

- `src/bioetl/domain/models/metadata.py` — BaseOutputMetadata, \*OutputExt классы

**DTOs:**

- `src/bioetl/domain/ports/metadata_coordinator.py` — Добавлены `version_before`, `total_bytes`, `partition_count`

**Services:**

- `src/bioetl/application/services/lineage/metadata_coordinator.py` — Обновлены create\_\*\_metadata методы

**Infrastructure:**

- `src/bioetl/infrastructure/storage/bronze_writer.py` — \_build_full_bronze_metadata
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

- `tests/unit/domain/models/test_metadata_output.py` — BaseOutputMetadata, \*OutputExt

### Architecture Tests

- `tests/architecture/test_metadata_output_contract.py` — Contract validation

## References

- RULES.md §2.4 — Lineage Requirements
- ADR-014 — Deterministic Writes (content hash)
- glossary.md — Ubiquitous Language definitions

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                 |
| ------------ | -------------------------------------------------------------------------- | ------ | ---------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-029-output-metadata-unification.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                               |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                         |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`     |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                             |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
