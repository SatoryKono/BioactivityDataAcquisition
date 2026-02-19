# Аудит актуальности плана рефакторинга (2026-02-15)

## Контекст проверки

Проверка выполнена по текущему `work` branch (HEAD), без предположений о состоянии `main`.

## Статус по промптам

### Prompt 1 — BaseFilterConfig (Шаг 1.2)

**Статус: Актуально, высокий приоритет.**

Подтверждено:

- `SilverFilterConfig` наследуется от `GoldFilterConfig`.
- Вся логика фильтрации сейчас находится в `GoldFilterConfig`.
- Инфраструктура использует временный мост `from-gold-filter-config()`.

**Корректировка:**

- Делать как обязательный шаг 1.
- Ввести `BaseFilterConfig` как единственный носитель логики.
- В `SilverFilterConfig` оставить фабрику `from-base()`.
- На 1 итерацию оставить совместимость: alias `from-gold-filter-config = from-base` (с deprecation-комментарием), затем удалить на фазе cleanup.

### Prompt 2 — Сужение типов write-mode (Шаг 1.3)

**Статус: Частично актуально, но не готово к «быстрому» применению.**

Подтверждено:

- `TableConfig` держит `SilverWriteMode | str` и `GoldWriteMode | str`.
- Есть дополнительные `| str` в сигнатурах сервисных фабрик и в convenience-свойствах `PipelineConfig`.

**Корректировка:**

- Сначала выполнить миграцию всех call-site на enum-only.
- Затем убрать `| str` одновременно в `TableConfig`, сервисных фабриках и (если сохраняются) свойствах `PipelineConfig`.
- Иначе будет «полурефакторинг» с несогласованной типизацией.

### Prompt 3 — Двойной формат source-конфигов (Шаг 2.3)

**Статус: Частично устарел по месту изменения.**

Подтверждено:

- Нормализация source-конфига уже реализована в `infrastructure/config-loader.py::-normalize-source-config`.
- Предложенный файл `composition/providers/-config-helpers.py` не является центром нормализации формата.

**Корректировка:**

- Реализовывать расширение именно в `-normalize-source-config` (infrastructure), добавив поддержку top-level flat формата (`api/client/batch` без `source`).

### Prompt 4 — effective\-\*\-table (Шаг 3.1)

**Статус: Актуально, средний приоритет.**

Подтверждено:

- В `PipelineConfig` есть only convenience-свойства, но нет `effective-silver-table/effective-gold-table`.

**Корректировка:**

- Добавить свойства до массовой миграции call-sites (Prompt 5).

### Prompt 5 — Миграция вызовов convenience-свойств (Шаг 3.2)

**Статус: Актуально, но объем больше заявленного.**

Подтверждено:

- Есть реальные использования `config.primary-keys`, `config.silver-table`, `config.gold-table`, `config.write-mode`, `config.gold-write-mode`, `config.on-schema-mismatch` в `application/` и `composition/`.

**Корректировка:**

- Разбить миграцию на 2 PR:
  1. application/core + application/services
  1. composition + CLI + tests
- После каждого PR — полный mypy/pytest прогон.

### Prompt 6 — Удаление convenience-свойств (Шаг 3.3)

**Статус: Актуально, только после Prompt 5.**

**Корректировка:**

- Добавить «gate»: grep по legacy-доступам должен быть пустым не только в `src/`, но и в `tests/` (кроме тестов на backward compatibility, если они остаются).

### Prompt 7 — entity names (document → publication)

**Статус: Актуально, но requires diff-аудит YAML перед массовой заменой.**

**Корректировка:**

- Сначала инвентаризация `document*` по всем конфигам и pipeline refs.
- Затем атомарная замена + smoke тесты загрузчика конфигов.

### Prompt 8 — Упрощение pipeline YAML

**Статус: Актуально, высокий риск регрессий.**

Подтверждено:

- В config-loader действительно есть авто-вычисление ряда полей.

**Корректировка:**

- Применять пакетно по провайдерам, начиная с `chembl/*`.
- Не смешивать в одном PR с rename директорий (Prompt 10).

### Prompt 9 — Унификация DQ-ключей

**Статус: Актуально, средний риск.**

**Корректировка:**

- Выполнять после стабилизации Prompt 8.
- До удаления fallback — убедиться, что нет legacy-ключей ни в конфиге, ни в tests fixtures.

### Prompt 10 — Переименование каталогов

**Статус: Актуально, но только как финальная миграция конфигов.**

Подтверждено:

- Загрузчики уже поддерживают dual-path (`quality/dq`, `filters/filter`).

**Корректировка:**

- Не использовать `cp -r` как основной путь (риски рассинхронизации); делать `git mv` + точечные обновления ссылок.
- Отдельный PR только на rename + docs updates.

### Prompt 11 — Архтесты и cleanup fallback

**Статус: Актуально, но prerequisites сейчас не выполнены.**

Подтверждено:

- Тесты/схемы пока еще явно поддерживают `dq-overrides` alias.

**Корректировка:**

- Разделить на 2 шага:
  1. Добавление новых тестов на рефакторинг (можно раньше).
  1. Удаление fallback/alias только после полной YAML-миграции.

----------------------------------------------------------------------

## Скорректированный порядок реализации (рекомендуемый)

### Wave A (типобезопасность и домен)

1. **A1:** Prompt 1 (BaseFilterConfig) + архитектурные тесты разделения типов.
1. **A2:** Prompt 4 (effective\-\*\-table).
1. **A3:** Prompt 5 (миграция call-sites, 2 PR).
1. **A4:** Prompt 6 (удаление convenience-свойств).
1. **A5 (опц.):** Prompt 2 (enum-only write modes) после A3/A4.

### Wave B (форматы конфигов)

6. **B1 (опц.):** Prompt 3 — flat source format в `config-loader`.
1. **B2:** Prompt 7 — document→publication.
1. **B3:** Prompt 8 — минимизация pipeline YAML.
1. **B4:** Prompt 9 — унификация DQ-ключей.

### Wave C (финализация)

10. **C1:** Prompt 10 — rename каталогов (`git mv`, без дублирования деревьев).
01. **C2:** Prompt 11 — cleanup fallback + документация + coverage gate.

----------------------------------------------------------------------

## Готовый набор задач к реализации

### Epic 1 — Domain Filtering Separation

- [ ] Создать `BaseFilterConfig` и перенести в него всю логику фильтрации.
- [ ] Перевести `GoldFilterConfig`/`SilverFilterConfig` на наследование от `BaseFilterConfig`.
- [ ] Заменить bridge-вызовы `from-gold-filter-config()` на `from-base()` в infrastructure.
- [ ] Добавить/обновить тесты: архитектурный + параметризованные unit-тесты общих фильтров.
- [ ] Прогон: `mypy --strict src/bioetl/`, `pytest tests/unit/domain/filtering/ -v`, `pytest tests/architecture/ -v`.

### Epic 2 — PipelineConfig API Cleanup

- [ ] Добавить `effective-silver-table`/`effective-gold-table`.
- [ ] Мигрировать все вызовы legacy convenience-свойств на `config.table.*` и `config.effective-*`.
- [ ] Удалить convenience-свойства из `PipelineConfig` после zero-usage gate.
- [ ] Прогон: `mypy --strict src/bioetl/`, `pytest tests/ -x --timeout=120`.

### Epic 3 — Source Config Compatibility (Optional)

- [ ] Добавить поддержку top-level flat source-формата в `-normalize-source-config`.
- [ ] Добавить тесты на старый+новый формат.
- [ ] Прогон: `pytest tests/ -k "source-config or adapter" -v`.

### Epic 4 — YAML Migration

- [ ] Переименовать entity names `document* -> publication*` в source/pipeline refs.
- [ ] Упростить pipeline YAML до convention-based минимального стиля (провайдерными пакетами).
- [ ] Унифицировать DQ ключи (`*-field-validations -> field-validations`, и т.д.).
- [ ] Прогон: `pytest tests/ -k "config or dq" -v`.

### Epic 5 — Config Paths Finalization

- [ ] Перенести каталоги на `quality/filters/schemas/-schema` через `git mv`.
- [ ] Обновить docs/ADR ссылки на новые пути.
- [ ] Удалить fallback-код и legacy alias (`dq-overrides`) только после подтвержденной миграции.
- [ ] Финальный прогон: `mypy --strict src/bioetl/`, `pytest tests/ -x --timeout=120`, `pytest --cov=src/bioetl --cov-fail-under=85`.
