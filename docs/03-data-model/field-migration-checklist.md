# Field Migration Checklist (breaking-now)

План применения канонических имён **без dual-write и без сохранения legacy-колонок**. Базируется на `docs/03-data-model/rf-naming-unification-plan.md` и `field-naming-unification-matrix.md`. Применяется ко всем source-пайплайнам (ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar).

## Шаг 0. Базовая фиксация
- [ ] Зафиксировать актуальные схемы Silver/Pandera/Gold (см. `field-catalog-source-pipelines.md`).
- [ ] Подтвердить канон имён и типов (taxonomy: float nullable-int; InChI Key: `inchi_key`).
- [ ] Оценить влияние на потребителей (BQ views, composite pipelines, downstream jobs).

## Шаг 1. Breaking rename в коде и схемах
- [ ] В трансформерах переименовать поля в канон и удалить legacy-колонки.
- [ ] В Pandera Silver/Gold схемах оставить только канонические имена.
- [ ] Обновить data_schema, DQ, field_groups, composite configs на новые имена.
- [ ] Выполнить REBUILD затронутых таблиц.

## Шаг 2. Документация и регистры
- [ ] Обновить `docs/03-data-model/rf-naming-unification-plan.md` и `field-naming-unification-matrix.md` статусом breaking-now.
- [ ] Обновить `docs/04-reference/pipelines/*` спецификации: показать новые имена, удалить legacy.
- [ ] Обновить `domain/mapping/*_fields.py` под канон (publication/molecule/taxonomy).

## Шаг 3. Тесты и детерминизм
- [ ] Unit/Pandera: схемы и конверторы (без legacy).
- [ ] Golden: набор и порядок колонок только в канонических именах.
- [ ] Determinism: повторный прогон даёт бит-в-бит идентичные артефакты.
- [ ] Composite/Integration: пайплайны собираются с новыми именами.

## Шаг 4. Финализация
- [ ] Repo-wide проверка на отсутствие legacy имён (кроме changelog/migration notes).
- [ ] Обновить CHANGELOG и миграционные заметки.
- [ ] Зафиксировать version bump/contract change.

