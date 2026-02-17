# Schema Review and Drift Register

## Purpose

Единый реестр для обязательной сквозной проверки покрытия по цепочке:

`Domain entity fields ↔ transformer output ↔ Silver schema ↔ Gold contract`

Этот файл используется как источник для CI drift-check.

## Reporting Format (MUST)

Используйте только единый табличный формат:

`Pipeline | Field | Location | Problem Type | Risk`

Где:

- **Pipeline** — canonical pipeline id (`provider_entity`)
- **Field** — имя поля/PK
- **Location** — слой(и), где обнаружена проблема
  (`domain`, `transformer`, `silver`, `gold` или связка через `->`)
- **Problem Type** — одно из:
  - `missing_required` (blocking)
  - `broken_pk` (blocking)
  - `additive_drift` (warning)
- **Risk** — `P1` / `P2`

## Drift Register

| Pipeline | Field  | Location | Problem Type | Risk   |
| -------- | ------ | -------- | ------------ | ------ |
| _none_   | _none_ | _none_   | _none_       | _none_ |

> При появлении drift удалите placeholder-строку `_none_` и внесите реальные
> записи в указанном формате.

## Ownership and SLA

| Problem Type       | Owner                                | SLA              |
| ------------------ | ------------------------------------ | ---------------- |
| `missing_required` | Pipeline Owner + Domain Owner        | ≤ 24h            |
| `broken_pk`        | Pipeline Owner + Data Platform Owner | ≤ 8h             |
| `additive_drift`   | Pipeline Owner                       | ≤ 5 рабочих дней |
