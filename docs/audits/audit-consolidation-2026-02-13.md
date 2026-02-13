# Консолидация архитектурных аудитов BioETL

Дата: 2026-02-13
Источники: 4 аудита из веток codex/conduct-architectural-audit-for-bioetl-{a9um58, ekp0my, ek16yo, px0bxe}

---

## 1. Сравнительная таблица аудитов

| Категория | a9um58 | ekp0my | ek16yo | px0bxe | **Корректная оценка** |
|-----------|--------|--------|--------|--------|-----------------------|
| Слоистая архитектура (15%) | **3/10** | **9/10** | **6/10** | **4/10** | **9/10** |
| Контракты и Ports (12%) | 8/10 | 9/10 | 8/10 | 7/10 | **9/10** |
| Medallion Architecture (12%) | 8/10 | 9/10 | 9/10 | 8/10 | **9/10** |
| Ошибки и Circuit Breaker (10%) | 9/10 | 8/10 | 9/10 | 9/10 | **9/10** |
| Блокировки и конкурентность (10%) | 10/10 | 9/10 | 9/10 | 9/10 | **9/10** |
| Валидация и DQ (10%) | 9/10 | 8/10 | 8/10 | 9/10 | **9/10** |
| Логирование и наблюдаемость (8%) | 8/10 | 9/10 | 8/10 | 8/10 | **8/10** |
| Тестирование (8%) | 6/10 | 4/10 | 5/10 | 8/10 | **7/10** |
| Безопасность и секреты (8%) | 8/10 | 8/10 | 7/10 | 6/10 | **8/10** |
| Документация (7%) | 8/10 | 7/10 | 8/10 | 8/10 | **8/10** |
| **Итого** | **7.49** | **8.18** | **7.70** | **7.42** | **8.63** |

---

## 2. Выявленные ошибки и неточности

### ОШИБКА 1 (КРИТИЧЕСКАЯ): Infrastructure → Domain импорты ошибочно классифицированы как нарушения

**Затронуты:** a9um58 (3/10), ek16yo (6/10), px0bxe (4/10)

Три из четырёх аудитов флагируют 99–146 импортов `from bioetl.domain.*` в infrastructure как
нарушения слоистой архитектуры. Это **фундаментальная ошибка интерпретации**.

**Факты:**

1. Матрица импортов ARCH-001 явно показывает: `infrastructure → domain = ✅`
2. Исключение EXC-012 в ai-selfreview-rules.md:
   > "Infrastructure зависит от domain by design — domain содержит чистые value objects,
   > entities, config и contracts (ports) без I/O."
3. Архитектурные тесты (`tests/architecture/test_di_compliance.py`,
   `test_layer_dependencies.py`) проверяют ТОЛЬКО обратную зависимость:
   **domain MUST NOT import infrastructure** — и этот тест проходит.
4. Нет ни одного архитектурного теста, запрещающего `infrastructure → domain.*`
5. Правило ARCH-008 ("Ports MUST импортироваться из фасада") относится к **портам** конкретно
   (100% portов импортируется через `bioetl.domain.ports` — проверено), а не ко ВСЕМ
   domain-модулям.

**Корректная классификация:** infrastructure → domain.types, domain.exceptions, domain.config,
domain.entities, domain.models, domain.value_objects и т.д. — штатная зависимость
по Hexagonal Architecture. Оценка "Слоистая архитектура" должна быть 9/10, а не 3–6/10.

**Влияние на итоговый балл:** +0.45–0.90 пунктов (от +3 до +6 по этой категории × 15% вес).

---

### ОШИБКА 2: Циклические импорты — ложный fail

**Затронуты:** a9um58 ("fail, ModuleNotFoundError: pandera"), ek16yo ("fail, отсутствует pandera")

Ошибка `ModuleNotFoundError: pandera` при `from bioetl.domain import *` — это отсутствие
зависимости в текущем окружении, а **не циклический импорт**. ekp0my и px0bxe подтверждают
`pass` при корректном окружении.

**Корректный результат:** Циклических импортов нет. Проблема — в неполноте dev-окружения.

---

### ОШИБКА 3: Coverage ошибочно помечен как "неподтверждённый"

**Затронуты:** a9um58, ekp0my, ek16yo (отметили coverage как неизвестный)

Файл `coverage.json` (3.5 MB, timestamp 2026-01-30) содержит результат **89.54%** coverage,
что превышает порог 85%. Только px0bxe обнаружил этот файл.

**Корректный результат:** Coverage = 89.54% ≥ 85%. Критерий TEST-001 соблюдён.

---

### ОШИБКА 4: detect-secrets ошибочно описан как "отсутствующий" в зависимостях

**Затронуты:** ekp0my, px0bxe (утверждают отсутствие пакета)

`detect-secrets>=1.4` присутствует в `pyproject.toml` дважды (строки 84 и 128).
Падение теста `test_no_hardcoded_secrets` в некоторых запусках — проблема инсталляции
окружения, а не декларации зависимостей.

**Корректная формулировка:** Зависимость объявлена; проблема в неполной установке
dev-зависимостей в конкретных sandbox-окружениях аудитов.

---

### ОШИБКА 5: Количество ошибок mypy — расхождение 37 vs 56

| Аудит | mypy errors |
|-------|-------------|
| a9um58 | 56 |
| ekp0my | 56 |
| ek16yo | 56 |
| px0bxe | 37 |

pyproject.toml содержит комментарий: "All layers now pass strict mypy checks."
Расхождение (37 vs 56) вероятно вызвано разными версиями mypy/стабов или разными
конфигурациями окружения. Ни один аудит не верифицировал версии инструментов.

**Рекомендация:** Зафиксировать точную версию mypy в CI и включить в отчёт.

---

### ОШИБКА 6: Bronze path "v1" — несуществующее требование

**Затронуты:** a9um58, ek16yo, px0bxe

Аудиты указывают отсутствие `v1` сегмента в Bronze path как отклонение. Но:

1. Документация `bronze_writer.py` (docstring): `REQ-DATA-002: Path format bronze/{provider}/{entity}/{date}/`
2. Код: `f"{provider}/{entity}/{date_str}/{filename}"`
3. В RULES.md **нет** требования `v1` в пути Bronze

Требование `v1` — артефакт промпта аудита, а не проектных правил.

**Корректная оценка:** Path format соответствует REQ-DATA-002. Нет нарушения.

---

### ОШИБКА 7: Средний размер модуля — мелкая неточность

| a9um58 | ekp0my | ek16yo | px0bxe |
|--------|--------|--------|--------|
| 221.08 | 222.08 | 222.08 | 222.08 |

Расхождение в a9um58 (221.08 vs 222.08). Не критично, но указывает на разное
подмножество файлов при подсчёте.

---

### НЕТОЧНОСТЬ 8: Несколько логгеров — не проблема

**Затронуто:** a9um58 (предлагает унификацию как P3 рефакторинг)

В infrastructure 3 логгера:
- `StructlogLogger` — основная реализация LoggerPort
- `NoOpLogger` — Null Object Pattern (EXC-003, явно разрешён)
- `UnifiedLogger` — расширенная реализация с run_id binding

Плюс `BootstrapLogger` в composition (для bootstrap-фазы до DI).

Это не "рассинхронизация практик", а штатный паттерн: разные реализации одного порта
для разных контекстов. Null Object Pattern документирован как исключение.

---

### НЕТОЧНОСТЬ 9: Plan [P1] a9um58 — предложение рефакторинга по ложному основанию

a9um58 предлагает как P1:
> "Ограничить infrastructure → domain до ports/VO-контрактов... вынести типы в
> application.contracts... адаптеры завязать на транспортные DTO"

Это **over-engineering** на основе ложного нарушения. Текущая архитектура корректна:
infrastructure зависит от domain by design. Предложенный рефакторинг создаст
ненужную промежуточную абстракцию и удвоит количество DTO без реальной пользы.

---

### НЕТОЧНОСТЬ 10: CI regex для проверки слоёв — ошибка в a9um58

a9um58 предлагает CI-метрику:
```
rg --pcre2 '^from bioetl\.domain\.(?!ports)' src/bioetl/infrastructure
```

Это заблокирует легитимные импорты domain.types, domain.exceptions и т.д.,
которые разрешены по ARCH-001 и EXC-012. Применение этой метрики сломает CI.

---

## 3. Скорректированный консолидированный план рефакторинга

### Пересчёт приоритетов

После удаления ложных нарушений, реальный score: **~8.63/10**.
Основные точки роста — тестирование (воспроизводимость) и mypy debt.

---

### [P1] RF-001: Устранить mypy strict debt

**Категория:** Types (TYPE), Testing (TEST)
**Текущий балл → Целевой:** 7→9 (Тестирование)
**Влияние на общий балл:** +0.16

**Проблема:**
37–56 ошибок mypy --strict (в зависимости от окружения). pyproject.toml заявляет
"All layers pass strict mypy", но это не подтверждается.

**Решение:**
1. Зафиксировать версию mypy в `pyproject.toml` (pin exact version)
2. Устранить ошибки по слоям: domain → application → infrastructure
3. Основные категории ошибок (по опыту подобных кодовых баз):
   - `unused-ignore` / `redundant-cast` — удалить лишние `# type: ignore`
   - Pandera `DataFrameModel` typing — использовать overrides в pyproject.toml
   - `untyped-decorator` — аннотировать Click/Pandera декораторы
4. Добавить `mypy --strict` в pre-commit hook

**Файлы:** `pyproject.toml`, `src/bioetl/domain/schemas/**`, `src/bioetl/infrastructure/storage/gold_writer.py`
**Критерий готовности:** `mypy src/bioetl --strict` → 0 errors
**Трудозатраты:** M

---

### [P1] RF-002: Обеспечить воспроизводимость dev-окружения

**Категория:** Testing (TEST), Security (SEC)
**Текущий балл → Целевой:** 7→9 (Тестирование)
**Влияние на общий балл:** +0.16

**Проблема:**
4 независимых запуска аудита показали нестабильность:
- `ModuleNotFoundError: pandas` / `pandera`
- `detect_secrets` не установлен
- `ruff format` не доступен
- Разные результаты mypy

**Решение:**
1. Создать единый `make audit-env` / `make setup-dev` target
2. Добавить smoke-test зависимостей в CI:
   ```bash
   python -c "import pandas; import pandera; import detect_secrets; import ruff"
   ```
3. Зафиксировать lock-file (если не используется uv.lock / poetry.lock)
4. Документировать минимальные требования к окружению для аудита

**Файлы:** `pyproject.toml`, `Makefile`, CI workflows
**Критерий готовности:** `make setup-dev && make lint && make test` стабильно проходит
**Трудозатраты:** S

---

### [P2] RF-003: Нормализовать и протестировать Bronze path contract

**Категория:** Medallion (ARCH)
**Текущий балл → Целевой:** 9→10
**Влияние на общий балл:** +0.12

**Проблема:**
Path format `{provider}/{entity}/{date}/{filename}` реализован, но нет
контрактного теста, гарантирующего его стабильность. Отсутствие теста позволяет
незаметно изменить формат.

**Решение:**
1. Добавить architecture test в `tests/architecture/` проверяющий:
   - Bronze path format: `{provider}/{entity}/{YYYY-MM-DD}/{filename}.jsonl.zst`
   - Silver path: Delta table location
   - Gold path: Delta table location
2. Документировать path policy в ADR (если не задокументирован)

**Файлы:** `tests/architecture/test_path_contracts.py` (новый),
`src/bioetl/infrastructure/storage/bronze_writer.py`
**Критерий готовности:** Тест блокирует изменение path format без обновления контракта
**Трудозатраты:** S

---

### [P2] RF-004: Добавить контрактный тест на Medallion clear policy

**Категория:** Medallion (ARCH-007)
**Текущий балл → Целевой:** 9→10
**Влияние на общий балл:** +0.06

**Проблема:**
ARCH-007 определяет: REBUILD → MUST clear Silver+Gold; INCREMENTAL → MUST NOT clear.
Но в аудитах нет подтверждения контрактного теста для этой матрицы.

**Решение:**
Добавить parametrized architecture test:
```python
@pytest.mark.parametrize("run_type,should_clear", [
    (RunType.REBUILD, True),
    (RunType.BACKFILL, True),
    (RunType.INCREMENTAL, False),
])
def test_medallion_clear_policy(run_type, should_clear): ...
```

**Файлы:** `tests/architecture/test_medallion_policy.py` (новый или расширение существующего)
**Критерий готовности:** Тест покрывает все 3 run type × 2 слоя
**Трудозатраты:** S

---

### [P3] RF-005: Консолидация документационных ссылок

**Категория:** Documentation
**Текущий балл → Целевой:** 8→9
**Влияние на общий балл:** +0.07

**Проблема:**
Все 4 аудита отмечают отсутствие файлов `01-domain-objects.md`, `02-etl-layers.md`,
`03-data-flow.md` и т.д. в `docs/00-project/`. При этом эквивалентные документы
существуют в `docs/02-architecture/`:
- `01-domain-layer.md` ≈ 01-domain-objects.md
- `data-layers.md` ≈ 02-etl-layers.md
- `data-flow.md` ≈ 03-data-flow.md

**Решение:**
1. Создать index-файл `docs/00-project/architecture-index.md` с каноническими ссылками
2. Либо создать symlinks/alias-файлы для часто запрашиваемых путей

**Файлы:** `docs/00-project/`, `docs/02-architecture/`
**Критерий готовности:** Все документы, упомянутые в аудиторском шаблоне, разрешаются
**Трудозатраты:** S

---

### [P3] RF-006: Чистка TODO/FIXME + formatter compliance

**Категория:** Documentation, Maintainability
**Текущий балл → Целевой:** 8→9
**Влияние на общий балл:** +0.04

**Проблема:**
23 TODO/FIXME в codebase. 1+ файл не проходит `ruff format --check`.

**Решение:**
1. Triage TODO/FIXME: конвертировать в GitHub issues или устранить
2. Запустить `ruff format src/` для нормализации
3. Добавить `ruff format --check` в pre-commit

**Файлы:** `src/bioetl/infrastructure/storage/gold_writer.py`, другие по результатам grep
**Критерий готовности:** `ruff format --check src tests` → 0 issues; TODO count ≤ 5
**Трудозатраты:** S

---

## 4. Roadmap

| Фаза | Задачи | Ожидаемый балл |
|-------|--------|----------------|
| Фаза 1 (неделя 1) | RF-001 (mypy), RF-002 (dev env) | 8.63 → 8.95 |
| Фаза 2 (неделя 2-3) | RF-003 (path tests), RF-004 (clear policy tests) | 8.95 → 9.13 |
| Фаза 3 (неделя 4+) | RF-005 (docs), RF-006 (cleanup) | 9.13 → 9.24 |

---

## 5. CI метрики контроля регресса (скорректированные)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|--------------|
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy strict | 0 errors | `mypy src/bioetl --strict` | Да |
| Domain purity | 0 violations | `grep -rn "from bioetl.infrastructure\|from bioetl.application" src/bioetl/domain/ --include="*.py"` | Да |
| Application isolation | 0 violations | `grep -rn "from bioetl.infrastructure" src/bioetl/application/ --include="*.py" \| grep -v TYPE_CHECKING` | Да |
| Port facade (ARCH-008) | 0 violations | `grep -rn "from bioetl.domain.ports\." src/bioetl/ --include="*.py"` (deep port imports) | Да |
| print() in production | 0 | `grep -rn "^\s*print(" src/bioetl/ --include="*.py"` | Да |
| Formatter | 0 issues | `ruff format --check src tests` | Да |
| Secret scan | 0 findings | `detect-secrets scan --all-files` | Да |
| Arch tests | all pass | `pytest tests/architecture/ -v` | Да |

> **ВАЖНО:** Метрика `infrastructure → domain(!=ports)` из аудитов a9um58, ek16yo, px0bxe
> является **ошибочной** и **НЕ ДОЛЖНА** использоваться. Infrastructure → domain — штатная
> зависимость по ARCH-001 и EXC-012.

---

## 6. Промпты для субагентов

### Промпт 1: RF-001 — mypy strict debt (py-debug-bot)

```
Задача: Устранить все ошибки mypy --strict в src/bioetl/

Контекст:
- pyproject.toml: strict = true, python_version = "3.11"
- Количество ошибок: 37-56 (зависит от окружения)
- Основные проблемы: unused-ignore, DataFrameModel typing, untyped decorators
- Важно: НЕ менять поведение кода, только типовые аннотации

Шаги:
1. Запустить: mypy src/bioetl --strict 2>&1 | tee /tmp/mypy_errors.txt
2. Классифицировать ошибки по категориям:
   - unused-ignore → удалить лишние # type: ignore
   - missing-return-type → добавить return type
   - untyped-decorator → аннотировать или добавить в overrides
   - incompatible-type → исправить сигнатуры
3. Устранять по слоям: domain → application → infrastructure
4. После каждого слоя: перезапустить mypy для регресс-контроля
5. Зафиксировать версию mypy в pyproject.toml: mypy = "==1.x.y"

Ограничения:
- НЕ добавлять blanket # type: ignore без error code
- НЕ менять runtime поведение
- НЕ отключать strict для целых модулей
- Pandera DataFrameModel: допустимо использовать overrides в pyproject.toml

Критерий: mypy src/bioetl --strict → 0 errors
```

### Промпт 2: RF-002 — Dev environment reproducibility (py-config-bot)

```
Задача: Обеспечить воспроизводимость dev-окружения BioETL

Контекст:
- 4 независимых аудита показали разные ошибки окружения
- detect-secrets, pandas, pandera — не установлены в sandbox
- Нет единой команды для полной настройки dev env

Шаги:
1. Проверить pyproject.toml: все dev-зависимости в [project.optional-dependencies]
2. Убедиться detect-secrets>=1.4 в test/dev группе
3. Создать/обновить Makefile target:
   ```makefile
   .PHONY: setup-dev
   setup-dev:
       uv pip install -e ".[dev,test]"
       python -c "import pandas; import pandera; import detect_secrets; print('OK')"

   .PHONY: audit-env-check
   audit-env-check:
       python -c "import pandas, pandera, detect_secrets, ruff, mypy; print('All audit deps OK')"
   ```
4. Документировать в README или CONTRIBUTING

Критерий: make setup-dev && make lint && make test проходит стабильно
```

### Промпт 3: RF-003 — Bronze path contract test (py-test-bot)

```
Задача: Добавить контрактный тест для Bronze/Silver/Gold path format

Контекст:
- Bronze path: {provider}/{entity}/{YYYY-MM-DD}/{filename}.jsonl.zst (REQ-DATA-002)
- Silver: Delta table
- Gold: Delta table
- Нет существующего теста, гарантирующего стабильность path format
- bronze_writer.py: _resolve_bronze_path() возвращает path string

Шаги:
1. Создать tests/architecture/test_path_contracts.py
2. Тесты:
   - test_bronze_path_format: проверить regex "{provider}/{entity}/{YYYY-MM-DD}/{uuid}.jsonl.zst"
   - test_bronze_path_no_v1: убедиться НЕТ "v1" в пути (соответствие REQ-DATA-002)
   - test_bronze_flat_structure: проверить flat_structure=True вариант
3. Использовать unit-test подход: создать BronzeWriter mock и вызвать _resolve_bronze_path
4. Добавить в tests/architecture/ для интеграции с CI

Ограничения:
- Следовать naming conventions из RULES.md
- Не менять production code
- Использовать pytest parametrize где уместно

Критерий: pytest tests/architecture/test_path_contracts.py -v → all pass
```

### Промпт 4: RF-004 — Medallion clear policy test (py-test-bot)

```
Задача: Добавить контрактный тест для ARCH-007 Medallion Clear Policy

Контекст:
- ARCH-007 определяет:
  - REBUILD → MUST clear Silver + Gold
  - BACKFILL → MUST clear Silver + Gold
  - INCREMENTAL → MUST NOT clear Silver/Gold
- Нужен parametrized architecture test

Шаги:
1. Найти существующие тесты medallion policy в tests/
2. Если нет — создать tests/architecture/test_medallion_clear_policy.py
3. Реализовать:
   ```python
   @pytest.mark.parametrize("run_type,should_clear_silver,should_clear_gold", [
       (RunType.REBUILD, True, True),
       (RunType.BACKFILL, True, True),
       (RunType.INCREMENTAL, False, False),
   ])
   def test_medallion_clear_policy(run_type, should_clear_silver, should_clear_gold):
       ...
   ```
4. Проверить через mock или inspection кода clear_silver/clear_gold вызовов

Ограничения:
- Следовать EXC-012: infrastructure может импортировать domain
- Не менять production code

Критерий: pytest tests/architecture/test_medallion_clear_policy.py -v → all pass
```

### Промпт 5: RF-005 — Documentation index (py-doc-bot)

```
Задача: Создать index документации для аудиторских проверок

Контекст:
- 4 аудита искали файлы 01-domain-objects.md...05-physical-layout.md в docs/00-project/
- Эквивалентные документы существуют в docs/02-architecture/:
  - 01-domain-layer.md, data-layers.md, data-flow.md и т.д.
- Нужна карта соответствий

Шаги:
1. Создать docs/00-project/architecture-index.md с:
   - Canonical links на все архитектурные документы
   - Mapping старых имён → актуальных путей
   - Дата последней синхронизации
2. Обновить docs/00-project/00-map.md (если существует) с новыми ссылками

Ограничения:
- НЕ создавать дублирующие документы
- Только ссылки и mapping

Критерий: Все документы из аудиторского шаблона разрешаются через index
```

### Промпт 6: RF-006 — TODO cleanup + formatter (py-audit-bot)

```
Задача: Triage TODO/FIXME и привести код к formatter compliance

Контекст:
- 23 TODO/FIXME/XXX/HACK в src/
- gold_writer.py не проходит ruff format --check
- Цель: TODO ≤ 5, formatter = 0 issues

Шаги:
1. Получить список: grep -rn "TODO\|FIXME\|XXX\|HACK" src/ --include="*.py"
2. Классифицировать каждый TODO:
   - Если устарел → удалить
   - Если актуален → конвертировать в GitHub issue и оставить ссылку
   - Если quick fix → исправить
3. Запустить ruff format src/
4. Проверить: ruff format --check src tests

Ограничения:
- НЕ менять логику кода при удалении TODO
- Сохранить комментарии, которые объясняют "почему"

Критерий: ruff format --check src tests → 0; grep TODO src/ | wc -l ≤ 5
```

---

## 7. Заключение

Из четырёх аудитов **наиболее точным** является **ekp0my** (8.18/10), хотя и он
занизил оценку тестирования (4/10 при фактическом coverage 89.54%).

Главная системная ошибка всех аудитов — неверная интерпретация матрицы импортов:
infrastructure → domain классифицировано как нарушение, хотя это штатная зависимость
по Hexagonal Architecture, явно разрешённая в ARCH-001 и EXC-012.

После коррекции реальный score проекта: **~8.63/10**, что соответствует статусу
"Production-ready, minor improvements needed". Основные точки роста — mypy debt
и воспроизводимость dev-окружения.
