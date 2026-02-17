# ADR-034: Schema↔Domain Configuration Pairs

## Status

Accepted

## Date

2026-02-15

## Context

BioETL использует Hexagonal Architecture. Domain слой определяет immutable
value objects (frozen dataclasses) для конфигурации. Infrastructure слой
определяет Pydantic модели для десериализации YAML файлов.

Оба слоя имеют классы с одинаковыми или похожими именами (например, DQConfig,
BaseClientConfig), что создаёт видимость дупликации при code review.

Ref: RULES.md §3 (Architecture), ai-selfreview-rules.md §7 (EXC-015).

## Decision

Разрешить одноимённые классы в domain и infrastructure при условии:

1. Domain класс — immutable value object (frozen dataclass) с бизнес-валидацией
1. Infrastructure класс — Pydantic model для YAML десериализации
1. Infrastructure модель имеет метод `to_domain()` для конвертации
1. Импорты всегда fully qualified (bioetl.domain.X vs bioetl.infrastructure.X)

## Known Pairs

| Domain               | Infrastructure                                     | Purpose            |
| -------------------- | -------------------------------------------------- | ------------------ |
| BaseClientConfig     | BaseClientConfig (schemas/base_schemas.py)         | HTTP client config |
| CircuitBreakerConfig | CircuitBreakerConfig (schemas/pipeline_config.py)  | Circuit breaker    |
| DQConfig             | DQConfig (schemas/pipeline_config.py)              | Data Quality       |
| DQReportConfig       | DQReportConfig (schemas/pipeline_config.py)        | DQ Reports         |
| InputFilterConfig    | BaseInputFilterConfig (schemas/pipeline_config.py) | Input filters      |

## Consequences

- grep по имени класса вернёт несколько результатов — это нормально
- Разработчик должен проверять import path для определения нужного класса
- Новые config objects должны следовать паттерну: Pydantic schema → to_domain() → dataclass

## Primary Key Governance (2026-02 update)

To align pipeline configs, Silver schemas, and Gold contracts, primary keys use canonical naming:

1. Canonical key names MUST end with `_id`.
1. Publication entities MUST use `publication_id` as the canonical PK.
1. Target entities MUST use `target_id` as the canonical PK.
1. Legacy provider keys (`doi`, `pmid`, `paper_id`, `openalex_id`, `accession`) are treated as aliases, not canonical PKs.

### Legacy Alias Policy

- Pipelines introducing canonical renames MUST dual-write canonical PK + legacy alias in Silver and Gold.
- Contracts and specs MUST document aliases via `legacy_key_aliases`.
- Deprecation window: **2 minor releases** from first dual-write release.
- After deprecation window, legacy alias MAY remain as non-key informational field, but MUST NOT be used as `primary_keys`/`primary_key`.

### Enforcement Points

- `configs/pipelines/*/*.yaml`: `primary_keys` stores canonical names only.
- Silver sink config: `sink.silver.primary_key` stores canonical names only.
- Gold contracts (`docs/04-reference/contracts/gold/*.json`): required list must contain canonical PK.

## Alternatives Considered

- YAML prefix (YamlDQConfig) — отвергнуто, избыточно
- Schema suffix (DQConfigSchema) — возможная альтернатива для будущих пар
