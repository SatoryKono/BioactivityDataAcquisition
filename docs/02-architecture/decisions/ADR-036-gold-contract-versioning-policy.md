---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-036: Gold Contract Versioning Policy

**Date:** 2026-02-18
**Decision makers:** @BioETL-Team
**Related:** ADR-018 (Gold Strict Validation), ADR-035 (JSON Field Typing Policy), ADR-026 (Composite Pipeline Pattern)

## Context

Schema audits (2026-02-17) выявили множественные потенциальные breaking changes в Gold контрактах:

- Переименование PK (`tissue-chembl-id` → `tissue-id`)
- Удаление legacy полей (journal aliases, ghost base-names)
- Продвижение полей из TRASH в Gold (language, license-url)
- Унификация типов (taxonomy IDs, list/JSON fields per ADR-035)

Без формальной политики версионирования breaking changes могут сломать downstream consumers без предупреждения. Необходимы чёткие правила для классификации изменений и управления миграцией.

## The Decision

Принять семантическое версионирование для Gold контрактов: `major.minor`.

### Классификация изменений

| Тип изменения | Version bump | Примеры |
|---------------|-------------|---------|
| Добавление nullable колонки | minor | Новое аналитическое поле |
| Добавление metadata/docs | patch (no bump) | Комментарии, описания |
| Переименование колонки | **major** | `tissue-chembl-id` → `tissue-id` |
| Удаление колонки | **major** | Удаление legacy journal fields |
| Изменение типа колонки | **major** | `string` → `float` для taxonomy |
| Изменение семантики колонки | **major** | `doi` означает разное |
| Перегруппировка (column order) | minor | Перемещение полей между группами |

### Обязательные артефакты для major bump

1. **ADR** с decision, migration plan, rollback criteria
2. **CHANGELOG** entry с old→new mapping и датой cutover
3. **Migration notes** с dual-service периодом и rollback triggers

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

## Related ADRs

- [ADR-018](ADR-018-gold-strict-validation.md): Strict validation зависит от стабильных контрактов
- [ADR-035](ADR-035-json-field-typing-policy.md): JSON typing migration — пример managed breaking change
- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite pipeline field groups подвержены breaking changes
