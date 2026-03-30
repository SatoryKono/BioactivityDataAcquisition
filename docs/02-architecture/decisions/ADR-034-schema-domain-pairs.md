---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-034: Schema↔Domain Configuration Pairs

**Date:** 2026-02-15

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
1. Infrastructure модель имеет метод `to-domain()` для конвертации
1. Импорты всегда fully qualified (bioetl.domain.X vs bioetl.infrastructure.X)
1. Для PK-полей обязательна cross-layer проверка соответствия между:
   - pipeline config (`business-primary-keys` + `technical-primary-key`),
   - Silver schema (Pandera),
   - Gold contract (JSON Schema).
     Проверка выполняется в CI как contract consistency gate.

### PK Consistency Control (Mandatory)

Для всех pipeline'ов canonical business PK имена в конфиге, Silver и Gold **MUST** быть одинаковыми
(`publication-id`, `target-id`, `molecule-id`, и т.д.).
Technical PK (`technical-primary-key`, обычно `entity-id`) MUST быть явно объявлен отдельно.

Legacy aliases допускаются только как временный migration слой и **MUST NOT** быть
единственным публичным PK в Gold контракте.

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
- Новые config objects должны следовать паттерну: Pydantic schema → to-domain() → dataclass

## Alternatives Considered

- YAML prefix (YamlDQConfig) — отвергнуто, избыточно
- Schema suffix (DQConfigSchema) — возможная альтернатива для будущих пар
