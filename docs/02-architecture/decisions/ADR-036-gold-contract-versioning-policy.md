______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-036: Gold Contract Versioning Policy

**Date:** 2026-02-18
**Status:** Accepted
**Decision makers:** @BioETL-Team
**Related:** ADR-018 (Gold Strict Validation), ADR-035 (JSON Field Typing Policy), ADR-026 (Composite Pipeline Pattern)

## Context

Schema audits (2026-02-17) выявили множественные потенциальные breaking changes в Gold контрактах:

- Переименование PK (`tissue-chembl-id` → `tissue-id`)
- Удаление legacy полей (journal aliases, ghost base-names)
- Продвижение полей из TRASH в Gold (language, license-url)
- Унификация типов (taxonomy IDs, list/JSON fields per ADR-035)

Без формальной политики версионирования breaking changes могут сломать downstream consumers без предупреждения. Необходимы чёткие правила для классификации изменений и управления миграцией.

## Decision

Принять семантическое версионирование для Gold контрактов: `major.minor`.

### Классификация изменений

| Тип изменения                  | Version bump    | Примеры                          |
| ------------------------------ | --------------- | -------------------------------- |
| Добавление nullable колонки    | minor           | Новое аналитическое поле         |
| Добавление metadata/docs       | patch (no bump) | Комментарии, описания            |
| Переименование колонки         | **major**       | `tissue-chembl-id` → `tissue-id` |
| Удаление колонки               | **major**       | Удаление legacy journal fields   |
| Изменение типа колонки         | **major**       | `string` → `float` для taxonomy  |
| Изменение семантики колонки    | **major**       | `doi` означает разное            |
| Перегруппировка (column order) | minor           | Перемещение полей между группами |

### Обязательные артефакты для major bump

1. **ADR** с decision, migration plan, rollback criteria
1. **CHANGELOG** entry с old→new mapping и датой cutover
1. **Migration notes** с dual-service периодом и rollback triggers

### Dual-service policy для breaking changes

- Минимум **2 релиза** параллельного обслуживания `vN` и `vN+1`
- Legacy aliases через compatibility layer (read-only)
- Cutover только после: adoption > 90%, parity checks pass, 0 critical DQ alerts (7 дней)

### Rollback criteria

Breaking change откатывается если:

- Contract validation failures > baseline + 30%
- Critical BI dashboards fail smoke tests
- DQ hard-fail rate > 5% батчей

## Justification

- **Предсказуемость:** downstream consumers знают, когда ожидать breaking changes
- **Безопасность:** dual-service период позволяет постепенную миграцию
- **Accountability:** обязательные артефакты документируют решения и ответственных
- **Rollback:** формализованные критерии позволяют быстро откатить неудачные миграции

## Consequences

### Positive

- Управляемые breaking changes с документированными migration paths
- Снижение риска silent breakage для downstream consumers
- Формализованные rollback criteria и dual-service policy
- Прозрачная классификация всех schema changes

### Negative

- Дополнительная нагрузка на поддержку dual-service (storage, compute)
- Overhead на документацию для каждого major bump
- Замедление delivery breaking changes из-за обязательного migration window

## Observability

- `contract-version-adoption`: доля consumers на каждой версии
- `contract-breaking-errors`: ошибки совместимости при чтении
- `dual-service-query-share`: распределение запросов между vN и vN+1
- `rollback-trigger-events`: срабатывания критериев отката

## References

- [ADR-018](ADR-018-gold-strict-validation.md): Strict validation зависит от стабильных контрактов
- [ADR-035](ADR-035-json-field-typing-policy.md): JSON typing migration — пример managed breaking change
- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite pipeline field groups подвержены breaking changes

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                     |
| ------------ | -------------------------------------------------------------------------- | ------ | -------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-036-gold-contract-versioning-policy.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                   |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                             |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`         |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                 |

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
