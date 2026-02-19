# Hash Policy Contract

## Назначение

Hash policy фиксирует детерминированные правила расчёта `content-hash` для пары `<provider>/<entity>`.
Файл политики хранится в `configs/hash-policy/<provider>/<entity>.yaml` и является машиночитаемым контрактом.

## Обязательная структура policy-файла

Каждый файл **MUST** содержать:

- `provider`, `entity`
- `contract.version` (SemVer)
- `contract.migration-note`
- `hash-policy.include-fields` (явный allow-list)
- `hash-policy.exclude-fields` (явный deny-list)
- `hash-policy.exclude-patterns`
- `hash-policy.normalization` c правилами:
  - `trim-strings`
  - `round-floats` (`precision`)
  - `dates` (`YYYY-MM-DD`)
  - `null-handling` (`nan-to-null`, `inf-to-null`)

## Правило изменения hash policy

Изменение hash policy (include/exclude/normalization) **MUST** сопровождаться:

1. **Version bump** в `contract.version` соответствующего `configs/hash-policy/<provider>/<entity>.yaml`.
1. **Migration note** в `contract.migration-note` с описанием влияния на downstream-потребителей и существующие Silver/Gold данные.
1. Обновлением snapshot-тестов стабильности hash на фиксированных fixtures.

## Проверка в тестах

Контракт покрывается тестами в `tests/unit/domain/hash-policy/`:

- Snapshot стабильности hash на фиксированных fixtures.
- Проверка, что policy-изменение требует version bump + migration note.
