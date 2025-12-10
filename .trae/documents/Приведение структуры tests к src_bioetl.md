## Цель
- Привести дерево `tests` к зеркалу слоёв и путей `src/bioetl` с соблюдением проектных правил.

## Текущее состояние (сводка)
- Есть корректные подпапки `tests/bioetl/application|domain|infrastructure`, но встречаются отклонения:
- Пайплайны ChEMBL: часть тестов агрегированы как `test_<entity>_pipeline.py` вместо per‑stage.
- Доп. корни: `tests/interfaces/cli`, `tests/pipelines/chembl` — вне `tests/bioetl/...`.

## Целевая структура
- Пайплайны: `tests/bioetl/pipelines/<provider>/<entity>/test_<stage>.py` для `extract|transform|validate|export`.
- Слои: `tests/bioetl/application/...`, `tests/bioetl/domain/...`, `tests/bioetl/infrastructure/...`, `tests/bioetl/interfaces/...` — соответствуют путям `src/bioetl/...`.
- Именование: `test_<module>.py`, без сетевых вызовов в unit‑тестах.

## План действий
- Переместить `tests/interfaces/cli/*` → `tests/bioetl/interfaces/cli/*`.
- Переместить `tests/pipelines/chembl/*` → `tests/bioetl/pipelines/chembl/*`.
- Для `chembl/{activity,assay,molecule,publication,target}`:
  - Разбить агрегаты `test_<entity>_pipeline.py` на `test_extract.py`, `test_transform.py`, `test_validate.py`, `test_export.py` (перенести соответствующие проверки).
  - Если проверки смешанные — сохранить логику, но разнести по стадиям с одинаковыми фикстурами.
- Оставить непайплайновые тесты в `tests/bioetl/application/...` (container, providers, hooks) — только привести имена к `test_<module>.py` при необходимости.
- Обновить импорты/фикстуры после перемещений, проверить `pytest.ini`/`pyproject.toml` (`testpaths`, `markers`).
- Удалить пустые папки и устаревшие файлы после разнесения.

## Дополнительно (по соответствию src)
- Добавить минимальные unit‑тесты (без классов) для модулей без покрытия, чтобы зеркало слоёв было полным: `infrastructure/http/retry.py`, `infrastructure/observability/*`, `interfaces/rest/server.py`, `interfaces/mq/*`, `application/files/csv_record_source.py`, `domain/enums.py`.

## Верификация
- Запустить `pytest -q`, убедиться, что все тесты проходят и покрытие ≥85%.
- Запустить правила `tests/project_rules/*` (naming, ABC/Default/Impl, Pandera), убедиться, что переструктурирование не нарушило проверки.
- Проверить инвентарь классов: число классов в `src` неизменно (baseline `total_classes: 208`).

## Риски и совместимость
- Переезды путей потребуют корректировки относительных импортов/фикстур.
- Добавление per‑stage файлов не меняет публичный API, сетей нет; классы не добавляются в `src`. Готов провести изменения атомарно и показать diff перед коммитом.