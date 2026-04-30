______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-034: Schema↔Domain Configuration Pairs

**Date:** 2026-02-15
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

BioETL использует Hexagonal Architecture. Domain слой определяет immutable
value objects (frozen dataclasses) для конфигурации. Infrastructure слой
определяет Pydantic модели для десериализации YAML файлов.

Оба слоя имеют классы с одинаковыми или похожими именами (например, DQConfig,
BaseClientConfig), что создаёт видимость дупликации при code review.

Ref: RULES.md §3 (Architecture), docs/00-project/ai/rules/bioetl-ai-rules.md (EXC-015 context).

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

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-034-schema-domain-pairs.md`     |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

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

## References

- `<link-or-path>`
