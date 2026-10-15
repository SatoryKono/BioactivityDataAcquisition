## Parent

#9639. Долгая пересборка mixin → один модуль — #9622. Здесь только **разблокировка текущего гейта**.

## Факт

`src/bioetl/domain/aggregates/batch.py` стал compatibility facade (ADR-059), а гейты всё ещё ждут implementation-модуль:

- нет `BatchCreated` / `collect_events()` / `def batch_id(self)` в `batch.py`;
- реестры ссылаются на удалённые `src/bioetl/domain/aggregates/_batch_record.py` и `_batch_status.py`;
- unreviewed SCC: `_batch_aggregate` ↔ `_batch_lifecycle` ↔ `_batch_mixins` ↔ `batch`;
- lazy-export inventory: `batch.py` unclassified;
- `_pipeline_run_mixins.py` 307 LOC > limit 305 (можно закрыть здесь или в ARCH-VG-05, если останется).

Тесты: `test_aggregate_boundaries.py`, `test_domain_aggregate_classification.py`, `test_domain_aggregate_invariant_registry.py`, `test_documentation_issues_6497_6498_closeout.py`, `test_runtime_import_scc.py`, `test_lazy_export_public_api_inventory.py`.

## Цель

Реестры, SCC allowlist/цикл и architecture-тесты соответствуют **текущему** дереву файлов. Публичный API `domain.aggregates` не ломать.

## Правки

1. Обновить invariant/classification registries: убрать мёртвые пути, указать живые модули.
2. Либо вернуть event/`collect_events`/property на фасад (re-export), либо сузить тесты к implementation-модулю — без ослабления инвариантов.
3. Разорвать SCC или добавить owner/rationale/review_date в `ACCEPTED_RUNTIME_SCCS`.
4. Классифицировать `batch.py` в lazy-export inventory.

## Не делать

Не повышать domain LOC cap. Полный collapse mixin-файлов — #9622.

## Definition of Done

- Указанные тесты зелёные.
- Нет ссылок на несуществующие `_batch_record.py` / `_batch_status.py`.
- SCC либо отсутствует, либо явно reviewed.
