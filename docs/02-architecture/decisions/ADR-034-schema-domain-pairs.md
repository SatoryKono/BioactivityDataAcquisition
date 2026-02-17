# ADR-034: Schema↔Domain Coverage Gate and Drift Governance

## Status

Accepted

## Date

2026-02-15

## Context

BioETL использует Hexagonal Architecture. Domain слой определяет immutable
value objects (frozen dataclasses) для бизнес-модели, а Infrastructure слой
определяет схемы сериализации/десериализации и технические контракты.

Ранее проверки соответствия между слоями выполнялись неравномерно, что
позволяло drift между Domain Entity, transformer output, Silver schema и Gold
contract проходить поздно или незаметно.

## Decision

### 1) Обязательная сквозная проверка покрытия (MUST)

Для каждого pipeline вводится обязательный audit-цепочки:

`Domain entity fields ↔ transformer output ↔ Silver schema ↔ Gold contract`

Минимальные требования:

1. `Domain entity field` MUST иметь явное решение в transformer output
   (mapped / intentionally dropped с обоснованием).
1. `Transformer output field` MUST быть валидируемым в Silver schema
   (или формально исключён с documented rationale).
1. `Gold required field` MUST иметь проверяемый upstream source
   (из Silver, enrichment, или deterministic derivation).
1. Primary key для Silver/Gold MUST быть консистентен и не может деградировать
   без ADR/контрактного изменения.

### 2) Drift-категории и уровни влияния

| Drift Category     | CI Behavior  | Severity | Definition                                             |
| ------------------ | ------------ | -------- | ------------------------------------------------------ |
| `missing_required` | **blocking** | P1       | Отсутствует обязательное поле в одной из точек цепочки |
| `broken_pk`        | **blocking** | P1       | Нарушен/утрачен primary key contract                   |
| `additive_drift`   | warning      | P2       | Добавлены новые поля без нарушения required/PK         |

### 3) Owner-ответственность и SLA (MUST)

| Drift Category     | Owner                                | SLA                                        |
| ------------------ | ------------------------------------ | ------------------------------------------ |
| `missing_required` | Pipeline Owner + Domain Owner        | Hotfix/rollback ≤ 24h                      |
| `broken_pk`        | Pipeline Owner + Data Platform Owner | Hotfix/rollback ≤ 8h                       |
| `additive_drift`   | Pipeline Owner                       | Документировать и закрыть ≤ 5 рабочих дней |

Pipeline Owner определяется через CODEOWNERS/ответственного за provider-entity
pipeline и отвечает за triage + remediation plan.

## Operationalization

- Единый формат drift-отчёта фиксируется в
  `docs/05-operations/verification/schema-review.md`.
- CI workflow `schema-drift-check.yml` выполняет автоматическую проверку:
  - fail для `missing_required` и `broken_pk`
  - warning для `additive_drift`

## Consequences

- Все изменения схем и трансформеров обязаны сопровождаться обновлением
  единого schema review отчёта.
- Drift-категории становятся операционными инцидентами с owner/SLA.
- review и release получают единый критерий блокировки по schema contract.

## Alternatives Considered

- Проверять только Silver↔Gold — отвергнуто (не покрывает потери в transformer).
- Неблокирующий CI для всех drift — отвергнуто (пропускает контрактные разрывы).
- SLA без owner assignment — отвергнуто (нет accountability).
