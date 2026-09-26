## Parent

#9639. Плановый shrink ниже 19 и смена wave-tags — #9626. Collapse `maintenance_api` — #9620.

## Факт (регрессия гейта)

`tests/architecture/test_private_module_imports.py`:

- `observed_count=21` > shrink-only `max_count=19`;
- новые пары: `interfaces/cli/commands/domains/maintenance/service_access.py` и `interfaces/cli/commands/vacuum.py` → `bioetl.composition._resource_management`.

Также:

- `test_interfaces_do_not_import_private_composition_modules` — те же импорты;
- freeze guard: строка `bioetl.composition._resource_management` в unit-тестах;
- #5567: facade `maintenance_api` получил импортёра `service_access.py`.

## Цель

CLI ходит только в публичный composition API (`maintenance_api` / typed registry / contracts). `observed_count` ≤ 19 **без** роста `max_count`.

## Правки

1. Заменить private import на публичный фасад (пока жив `maintenance_api`) или на contracts/registry.
2. Убрать внутренний модуль из unit-test string freeze, если тесты больше не должны его цитировать.
3. Не ставить `STRICT_PRIVATE_IMPORT_GUARD = True`, пока live > 0 (#9626).

## Definition of Done

- `test_private_module_imports.py` и freeze-guard на `_resource_management` зелёные.
- `max_count` не вырос (остаётся 19 или ниже live после фикса).
- Дальнейший shrink < 19 остаётся в #9626.
