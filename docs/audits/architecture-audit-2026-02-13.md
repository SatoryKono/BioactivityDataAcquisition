# Architecture Audit Report

Date: 2026-02-13
Scope: `src/bioetl/**`, `docs/00-project/agents/AGENT.md`, `docs/00-project/RULES.md`, документы `docs/02-architecture/**`.

## Примечание по входным документам

Запрошенные файлы `docs/00-project/01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не обнаружены. Для аудита использованы: `docs/02-architecture/01-domain-layer.md`, `docs/02-architecture/data-layers.md`, `docs/02-architecture/data-flow.md`, `docs/02-architecture/module-consolidation-migration-requirements.md`, `docs/03-guides/local-storage-layout.md`.

## Часть 1. Объективные метрики

| Метрика               | Команда/метод                                                                  | Значение                                     |
| --------------------- | ------------------------------------------------------------------------------ | -------------------------------------------- |
| Покрытие тестами      | `.venv/Scripts/python.exe -m pytest tests/ --cov=src/bioetl --cov-report=term` | [данные отсутствуют: прогон прерван на ~60%] |
| Ошибки mypy           | `mypy src/bioetl --strict`, подсчёт `error:`                                   | 56                                           |
| Циклические импорты   | `python -c "from bioetl.domain import *"`                                      | fail (отсутствует `pandera`)                 |
| Количество классов    | `rg '^class ' src --glob '*.py'` + подсчёт строк                               | 887                                          |
| Количество файлов .py | `find src -name '*.py'` + подсчёт строк                                        | 542                                          |
| Средний размер модуля | Python-скрипт по `src/bioetl/*.py`                                             | 222.08 строк (517 файлов в `src/bioetl`)     |
| TODO/FIXME в коде     | \`rg -e 'TODO                                                                  | FIXME                                        |
| Использование print() | `rg 'print\(' src/bioetl --glob '*.py'` + подсчёт строк                        | 0                                            |
| Hardcoded secrets     | \`rg -e '(api_key                                                              | password                                     |

## Часть 2. Оценка по 10 категориям

### 1) Слоистая архитектура — 6/10 (вес 15%, вклад 0.90)

- Позитив: `domain` не импортирует `application`/`infrastructure`.
- Нарушения: инфраструктура массово импортирует `bioetl.domain.*` вне `domain.ports` (например, `local_checkpoint.py`, `chembl/client.py`).

### 2) Контракты и Ports — 8/10 (вклад 0.96)

- `domain/ports/` активно использует `typing.Protocol`.
- Инфраструктурные адаптеры инжектят зависимости через порты.
- Ограничение: присутствуют прямые импорты доменных модулей в инфраструктуре.

### 3) Medallion Architecture — 9/10 (вклад 1.08)

- Bronze: JSONL + zstd реализован.
- Silver/Gold: используются Delta Lake writer-операции.
- Path/layout соответствуют архитектурным документам.

### 4) Обработка ошибок и Circuit Breaker — 9/10 (вклад 0.90)

- ErrorClassifier покрывает critical/recoverable/DQ классы.
- Circuit Breaker реализован со state machine, threshold=5, timeout=300s, метриками.

### 5) Блокировки и конкурентность — 9/10 (вклад 0.90)

- `MemoryLock` поддерживает TTL, heartbeat, fencing token, safety guard (`validate_owner`).
- Соответствует локальной модели ADR-010 (без Redis).

### 6) Валидация и DQ — 8/10 (вклад 0.80)

- Есть Pandera-валидаторы Silver/Gold.
- Есть Quarantine-процессы и DQ-порты.
- Content hash реализован с нормализацией и исключением системных полей.

### 7) Логирование и наблюдаемость — 8/10 (вклад 0.64)

- Есть UnifiedLogger/StructlogLogger, run_id обязателен.
- `print()` в production-коде не найден.
- Метрики присутствуют, но полнота instrumentation требует отдельного аудита.

### 8) Тестирование — 5/10 (вклад 0.40)

- Тестовая база большая (11k+ collected).
- Целевой coverage (≥85%) в этом запуске не подтверждён.
- `mypy --strict`: 56 ошибок.

### 9) Безопасность и секреты — 7/10 (вклад 0.56)

- 14 regex-попаданий в основном выглядят как проброс значений, не literal secrets.
- Явные hardcoded token literals данным паттерном не обнаружены.

### 10) Документация и сопровождаемость — 8/10 (вклад 0.56)

- Архитектурная документация и ADR хорошо представлены.
- `CHANGELOG.md` присутствует.
- Часть запрошенных путей отсутствует.

## Часть 3. Сводка

### 3.1. Сводная таблица

| #         | Категория                   |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                         |
| --------- | --------------------------- | -------: | -----: | ------------: | -------------------------------------------------------- |
| 1         | Слоистая архитектура        |      15% |      6 |          0.90 | infra -> domain (не только ports)                        |
| 2         | Контракты и Ports           |      12% |      8 |          0.96 | Protocol-архитектура есть, но есть прямые domain-импорты |
| 3         | Medallion Architecture      |      12% |      9 |          1.08 | Bronze JSONL+zstd, Silver/Gold Delta                     |
| 4         | Ошибки и Circuit Breaker    |      10% |      9 |          0.90 | Классификация + CB + metrics                             |
| 5         | Блокировки и конкурентность |      10% |      9 |          0.90 | TTL/heartbeat/fencing/safety guard                       |
| 6         | Валидация и DQ              |      10% |      8 |          0.80 | Pandera + Quarantine + content hash                      |
| 7         | Логирование/наблюдаемость   |       8% |      8 |          0.64 | UnifiedLogger, run_id, без print                         |
| 8         | Тестирование                |       8% |      5 |          0.40 | Coverage не подтверждён, mypy=56                         |
| 9         | Безопасность/секреты        |       8% |      7 |          0.56 | Literal secrets не подтверждены                          |
| 10        | Документация                |       7% |      8 |          0.56 | ADR/доки сильные, есть отсутствующие пути                |
| **Итого** |                             | **100%** |        | **7.70 / 10** |                                                          |

### 3.2. Интерпретация

**7.70 / 10** → требуется рефакторинг, но система работоспособна.

### 3.3. План рефакторинга

#### [P1] Ужесточить импорт-границы инфраструктуры

- **Категория**: 1, 2
- **Текущий балл -> целевой**: 6 -> 9
- **Влияние**: +0.45
- **Проблема**: инфраструктура импортирует `domain` вне портов.
- **Решение**: сокращение прямых domain-импортов, перенос зависимостей к портам/DTO.
- **Файлы**: `src/bioetl/infrastructure/checkpoint/local_checkpoint.py`, `src/bioetl/infrastructure/adapters/chembl/client.py`, смежные адаптеры.
- **Риски**: типовые регрессии и сериализация.
- **Критерий готовности**: 0 нарушений правила `infra -> domain (кроме ports)`.
- **Трудозатраты**: M.

#### [P1] Довести mypy strict до green

- **Категория**: 8
- **Текущий балл -> целевой**: 5 -> 8
- **Влияние**: +0.24
- **Проблема**: 56 ошибок mypy.
- **Решение**: устранить типовые несоответствия, доаннотировать публичный API.
- **Файлы**: `src/bioetl/**`.
- **Риски**: изменение публичных сигнатур.
- **Критерий готовности**: `mypy src/bioetl --strict` = 0 errors.
- **Трудозатраты**: M/L.

#### [P2] Формализовать coverage gate

- **Категория**: 8
- **Текущий балл -> целевой**: 5 -> 8
- **Влияние**: +0.24
- **Проблема**: coverage не подтверждён воспроизводимо.
- **Решение**: отдельный быстрый CI-профиль + nightly full-profile.
- **Файлы**: `pytest.ini`, CI workflow.
- **Риски**: рост времени CI.
- **Критерий готовности**: стабильный `--cov-fail-under=85`.
- **Трудозатраты**: S/M.

#### [P2] Усилить security checks для секретов

- **Категория**: 9
- **Текущий балл -> целевой**: 7 -> 9
- **Влияние**: +0.16
- **Проблема**: regex не разделяет «проброс» и «утечку».
- **Решение**: semgrep/gitleaks + allowlist.
- **Файлы**: CI/pre-commit.
- **Риски**: ложные срабатывания.
- **Критерий готовности**: 0 high-severity findings.
- **Трудозатраты**: S.

#### [P3] Консолидация ссылок документации

- **Категория**: 10
- **Текущий балл -> целевой**: 8 -> 9
- **Влияние**: +0.07
- **Проблема**: часть ожидаемых путей отсутствует.
- **Решение**: alias/index-страницы и карта миграции путей.
- **Файлы**: `docs/00-project/`, `docs/02-architecture/`.
- **Риски**: низкие.
- **Критерий готовности**: все canonical-ссылки разрешаются.
- **Трудозатраты**: S.

### 3.4. Roadmap

- **Фаза 1 (неделя 1-2)**: P1 (границы слоёв + mypy), ожидаемо 7.70 -> 8.35.
- **Фаза 2 (неделя 3-4)**: P2 (coverage + security checks), ожидаемо 8.35 -> 8.75.
- **Фаза 3 (неделя 5+)**: P3 (документация), ожидаемо 8.75 -> 8.82.

## Часть 4. CI метрики контроля регресса

| Метрика             | Порог      | Команда                                                                     | Блокирует PR |
| ------------------- | ---------- | --------------------------------------------------------------------------- | ------------ |
| Coverage            | >=85%      | `pytest --cov=src/bioetl --cov-fail-under=85`                               | Да           |
| mypy errors         | 0          | `mypy src/bioetl --strict`                                                  | Да           |
| Циклические импорты | 0          | `PYTHONPATH=src python -c "from bioetl.domain import *"` + dep-check script | Да           |
| Нарушения слоёв     | 0          | `rg 'from bioetl\.domain(?!\.ports)' src/bioetl/infrastructure -n -P`       | Да           |
| print() в коде      | 0          | `rg 'print\(' src/bioetl --glob '*.py'`                                     | Да           |
| Hardcoded secrets   | 0 critical | `gitleaks detect --source .`                                                | Да           |

## Verification Log

- `mypy src/bioetl --strict 2>&1 | grep -c "error:"`
- `PYTHONPATH=src python -c "from bioetl.domain import *"`
- `rg '^class ' src --glob '*.py' | wc -l`
- `find src -name '*.py' | wc -l`
- `rg -e 'TODO|FIXME|XXX|HACK' src | wc -l`
- `rg 'print\(' src/bioetl --glob '*.py' | wc -l`
- `rg -e '(api_key|password|secret)\s*=' src | wc -l`
- `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term-missing` (прерван вручную)
