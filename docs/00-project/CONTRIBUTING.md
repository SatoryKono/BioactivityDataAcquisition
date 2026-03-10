# Contributing to BioETL

## Typed self-dispatch rule

- В production-коде (`src/bioetl/`) запрещён паттерн `getattr(self, "...")`.
- Вместо динамического диспетча по `self` используйте явный типизированный контракт:
  - `Protocol` с обязательными методами/атрибутами, или
  - abstract base mixin с обязательными методами.
- При ограничениях MRO допускается только локальный `type: ignore[...]` с пояснением причины.

Проверка закреплена в `tests/architecture/test_no_getattr_self_string.py`.
