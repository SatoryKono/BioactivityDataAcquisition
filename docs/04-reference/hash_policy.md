# Hash Policy Contract

## Назначение

Hash policy фиксирует детерминированные правила расчёта `content_hash` для пары `<provider>/<entity>`.
Файл политики хранится в `configs/hash_policy/<provider>/<entity>.yaml` и является машиночитаемым контрактом.

## Обязательная структура policy-файла

Каждый файл **MUST** содержать:

- `provider`, `entity`
- `contract.version` (SemVer)
- `contract.migration_note`
- `hash_policy.include_fields` (явный allow-list)
- `hash_policy.exclude_fields` (явный deny-list)
- `hash_policy.exclude_patterns`
- `hash_policy.normalization` c правилами:
  - `trim_strings`
  - `round_floats` (`precision`)
  - `dates` (`YYYY-MM-DD`)
  - `null_handling` (`nan_to_null`, `inf_to_null`)

## Правило изменения hash policy

Изменение hash policy (include/exclude/normalization) **MUST** сопровождаться:

1. **Version bump** в `contract.version` соответствующего `configs/hash_policy/<provider>/<entity>.yaml`.
1. **Migration note** в `contract.migration_note` с описанием влияния на downstream-потребителей и существующие Silver/Gold данные.
1. Обновлением snapshot-тестов стабильности hash на фиксированных fixtures.

## Проверка в тестах

Контракт покрывается тестами в `tests/unit/domain/hash_policy/`:

- Snapshot стабильности hash на фиксированных fixtures.
- Проверка, что policy-изменение требует version bump + migration note.
