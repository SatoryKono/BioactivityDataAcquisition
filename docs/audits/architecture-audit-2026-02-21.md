# Architecture Audit Report

Date: 2026-02-21
Scope: `src/bioetl/**`, `tests/**`, `docs/00-project/RULES.md`, `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`

## 0) Проверенные документы

- Прочитан конституционный документ: `docs/00-project/RULES.md`.
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md` в репозитории не найдены
  (`find docs -type f | rg '01-domain-objects|02-etl-layers|03-data-flow|04-duplication-reduction|05-physical-layout'` вернул пусто). Статус: **[данные отсутствуют]**.
- Учитывалась оговорка ADR-010 о Local-Only deployment и `MemoryLock` как допустимой целевой реализации.

## 1) Объективные метрики

| Метрика                                        | Команда/метод                                                                            |                                         Значение |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------- | -----------------------------------------------: |
| Покрытие тестами                               | `./.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term`                 | **[данные отсутствуют: таймаут 180с, EXIT 124]** |
| Ошибки mypy                                    | `./.venv/bin/python -m mypy src/bioetl --strict 2>&1` + `grep -c 'error:' /tmp/mypy.out` |                                        **0 шт.** |
| Циклические импорты (базовая проверка импорта) | `./.venv/bin/python -c 'import bioetl.domain; print("pass")'`                            |                                         **pass** |
| Количество классов                             | `rg '^class ' src --glob '*.py' \| wc -l`                                                |                                      **936 шт.** |
| Количество файлов `.py`                        | `find src -name '*.py' \| wc -l`                                                         |                                      **570 шт.** |
| Средний размер модуля (`src/bioetl`)           | Python-скрипт: сумма строк / кол-во файлов                                               |                                 **219.15 строк** |
| TODO/FIXME/XXX/HACK                            | `rg -n -e 'TODO\|FIXME\|XXX\|HACK' src \| wc -l`                                         |                                        **2 шт.** |
| Использование `print()`                        | `rg 'print\(' src/bioetl --glob '*.py' \| wc -l`                                         |                                        **0 шт.** |
| Hardcoded secrets (эвристика по assignment)    | `rg -n -e '(api_key\|password\|secret)\s*=' src \| wc -l`                                |   **14 шт. (эвристика; не подтверждает утечку)** |

## 2) Детальная оценка по 10 категориям

### 2.1 Слоистая архитектура (вес 15%)

**Проверки границ из задания:**

- `domain -> infrastructure`: 0
- `domain -> application`: 0
- `application -> interfaces`: 0
- `infrastructure -> application`: 0

**Наблюдение (по более строгому правилу из аудиторского промпта):** в `infrastructure` есть множественные импорты из `bioetl.domain.*` вне `domain.ports`.
Примеры:

```python
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.normalization import normalize_doi
```

`src/bioetl/infrastructure/adapters/crossref/client.py:24-25`

```python
from bioetl.domain.medallion import Layer, SilverWriteMode, WriteMode, WriteModePolicy
```

`src/bioetl/infrastructure/storage/silver_writer.py:50`

**Оценка:** **6/10** (формальные проверки из задания пройдены, но по строгому профилю есть >10 зависимостей infra→domain не только через Ports).

### 2.2 Контракты и Ports (вес 12%)

- В `domain/ports` системно используются `typing.Protocol` (много контрактов: storage, locking, observability, data_source и др.).
- В `infrastructure` реализации адаптеров привязываются к портам.

**Оценка:** **8/10** (архитектурно зрелая система портов, но есть обходы через прямые доменные импорты в infrastructure).

### 2.3 Medallion Architecture (вес 12%)

**Позитивные подтверждения:**

- Bronze writer явно декларирует JSONL + zstd и path contract.
- Silver writer использует `deltalake.write_deltalake` и merge/upsert.
- Gold writer требует strict schema для `write_gold` и поддерживает SCD2 режим.
- Есть vacuum API в Silver writer + параметры retention в runtime config.

**Оценка:** **9/10**.

### 2.4 Обработка ошибок и Circuit Breaker (вес 10%)

- Реализован полноценный Circuit Breaker (threshold=5, timeout=300s, HALF_OPEN probe, метрики state/trips/success/failure).
- В проекте присутствуют доменные исключения и классификаторы ошибок.

**Оценка:** **9/10**.

### 2.5 Блокировки и конкурентность (вес 10%)

- `MemoryLock` реализует acquire/release/heartbeat/TTL + background checker.
- Реализованы `FencingToken`, `validate_owner` (Safety Guard), `validate_fencing_token`.
- Соответствует ADR-010 (Local-only).

**Оценка:** **10/10**.

### 2.6 Валидация и DQ (вес 10%)

- Есть Pandera-валидация (включая Silver/Gold pathways).
- Есть quarantine подсистема (`src/bioetl/infrastructure/quarantine/*`).
- В RULES зафиксированы soft/hard thresholds 5%/20%; в коде есть DQ конфиги и DQ сервисы.

**Оценка:** **8/10** (не доказано, что все сущности покрыты одинаково; для полной верификации нужен полный интеграционный прогон).

### 2.7 Логирование и наблюдаемость (вес 8%)

- `print()` в `src/bioetl` не найдено.
- Архитектура через `LoggerPort`, `MetricsPort`, `TracingPort` и NoOp-реализации прослеживается.
- Circuit breaker эмитит метрики.

**Оценка:** **8/10**.

### 2.8 Тестирование (вес 8%)

- Полный запуск coverage не завершился в отведённом времени (таймаут).
- При этом архитектурные тесты запускаются локально успешно: `tests/test_architecture.py` (18 passed).
- Есть contract-тесты и VCR-фикстуры/кассеты (`tests/fixtures/vcr*`).

**Оценка:** **6/10** (из-за отсутствия подтверждённого процента покрытия).

### 2.9 Безопасность и секреты (вес 8%)

- Эвристика по `api_key|password|secret` дала 14 совпадений, но это в основном прокидывание параметров/полей, не hardcoded literal secrets.
- Для однозначного вывода о PII hashing/salt rotation нужно целевое ревью security-paths.

**Оценка:** **7/10**.

### 2.10 Документация и сопровождаемость (вес 7%)

- Есть `CHANGELOG.md`, ADR-документы, большой объём guide/reference.
- Запрошенная часть companion-документов отсутствует под указанными именами.

**Оценка:** **7/10**.

## 3) Сводная таблица

| #         | Категория                       |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                                                |
| --------- | ------------------------------- | -------: | -----: | ------------: | ------------------------------------------------------------------------------- |
| 1         | Слоистая архитектура            |      15% |      6 |          0.90 | Формальные boundary-check pass; при строгом профиле есть infra→domain вне ports |
| 2         | Контракты и Ports               |      12% |      8 |          0.96 | Широкое использование Protocol в domain/ports                                   |
| 3         | Medallion Architecture          |      12% |      9 |          1.08 | Bronze JSONL+zstd, Silver Delta merge, Gold strict/SCD2                         |
| 4         | Ошибки и Circuit Breaker        |      10% |      9 |          0.90 | Полноценный CB + метрики                                                        |
| 5         | Блокировки и конкурентность     |      10% |     10 |          1.00 | MemoryLock + heartbeat + fencing + safety guard                                 |
| 6         | Валидация и DQ                  |      10% |      8 |          0.80 | Pandera + Quarantine + DQ конфиги                                               |
| 7         | Логирование и observability     |       8% |      8 |          0.64 | Port-based observability, print()=0                                             |
| 8         | Тестирование                    |       8% |      6 |          0.48 | Coverage % не подтверждён из-за таймаута                                        |
| 9         | Безопасность и секреты          |       8% |      7 |          0.56 | Hardcoded literal secrets не подтверждены                                       |
| 10        | Документация и сопровождаемость |       7% |      7 |          0.49 | ADR/CHANGELOG есть, часть запрошенных docs отсутствует                          |
| **Итого** |                                 | **100%** |        | **7.81 / 10** |                                                                                 |

## 3.2 Интерпретация общего балла

**7.81 / 10** → *«Требуется рефакторинг, но система работоспособна»*.

## 3.3 План рефакторинга

### [P1] Закрыть строгие нарушения зависимостей infrastructure→domain (кроме ports)

- **Категория:** 1 (Слоистая архитектура)
- **Текущий балл → Целевой:** 6 → 9
- **Влияние на общий балл:** +0.45
- **Проблема:** инфраструктурные модули импортируют доменные сущности/утилиты, напр. `crossref/client.py`, `silver_writer.py`, `gold_writer.py`.
- **Решение:**
  1. Свести imports в infrastructure к `bioetl.domain.ports` + минимальные shared contracts;
  1. вынести тех. типы в neutral contracts package (если нужны обеим сторонам);
  1. зафиксировать import-linter правило в CI.
- **Файлы (первые кандидаты):**
  - `src/bioetl/infrastructure/adapters/crossref/client.py`
  - `src/bioetl/infrastructure/storage/silver_writer.py`
  - `src/bioetl/infrastructure/storage/gold_writer.py`
- **Риски:** массовый рефакторинг интерфейсов, риск регрессий в адаптерах.
- **Критерий готовности:** `infrastructure -> domain` только через разрешённые контракты/ports, подтверждено автоматическим правилом.
- **Трудозатраты:** **M** (дни).

### [P1] Стабилизировать CI-метрику coverage (>=85%)

- **Категория:** 8 (Тестирование)
- **Текущий балл → Целевой:** 6 → 8
- **Влияние на общий балл:** +0.16
- **Проблема:** локальный полный coverage-run не завершился в 180с (нет объективного %).
- **Решение:** оптимизировать job (разделить test matrix, cache, selective suites), добавить обязательный `--cov-fail-under=85`.
- **Файлы:** CI workflow + docs testing.
- **Риски:** увеличение времени CI при неправильной настройке.
- **Критерий готовности:** стабильный и повторяемый отчёт coverage в CI.
- **Трудозатраты:** **S/M**.

### [P2] Формализовать DQ coverage-report по сущностям

- **Категория:** 6 (Валидация и DQ)
- **Текущий балл → Целевой:** 8 → 9
- **Влияние на общий балл:** +0.10
- **Проблема:** трудно автоматически доказать полный охват Pandera/thresholds для всех entity.
- **Решение:** добавить генератор DQ матрицы (entity -> schema -> quarantine policy -> threshold) и fail при пропусках.
- **Файлы:** `scripts/` + `tests/contract/` + docs.
- **Риски:** ложные срабатывания при миграциях схем.
- **Критерий готовности:** machine-readable DQ coverage matrix в CI artifacts.
- **Трудозатраты:** **M**.

### [P2] Ужесточить security-проверки на утечки секретов

- **Категория:** 9 (Безопасность)
- **Текущий балл → Целевой:** 7 → 9
- **Влияние на общий балл:** +0.16
- **Проблема:** текущая grep-эвристика шумная, не различает literal secret и безопасный flow.
- **Решение:** добавить gitleaks/trufflehog в CI + policy test на запрет hardcoded literals + redaction checks для логов.
- **Файлы:** `.gitleaks.toml`, CI workflows, `tests/security/*`.
- **Риски:** потребуются baseline-исключения.
- **Критерий готовности:** zero high-severity secret findings в PR gate.
- **Трудозатраты:** **S/M**.

### [P3] Упорядочить архитектурную документацию (алиасы и индекс)

- **Категория:** 10 (Документация)
- **Текущий балл → Целевой:** 7 → 8
- **Влияние на общий балл:** +0.07
- **Проблема:** запрошенные документы не найдены по ожидаемым именам.
- **Решение:** добавить mapping/aliases в `architecture-index.md` (legacy -> current docs paths).
- **Файлы:** `docs/00-project/architecture-index.md` и related guides.
- **Риски:** минимальные.
- **Критерий готовности:** все legacy-ссылки резолвятся через индекс/redirect-map.
- **Трудозатраты:** **S**.

## 3.4 Roadmap

- **Фаза 1 (неделя 1-2):** P1 (dependency boundaries + coverage gate). Ожидаемый общий балл: **~8.4**.
- **Фаза 2 (неделя 3-4):** P2 (DQ matrix + secrets gate). Ожидаемый общий балл: **~8.7**.
- **Фаза 3 (неделя 5+):** P3 (doc aliases/index). Ожидаемый общий балл: **~8.8**.

## 4) Метрики контроля регресса для CI

| Метрика                    |     Порог | Команда                                                                                                     | Блокирует PR |
| -------------------------- | --------: | ----------------------------------------------------------------------------------------------------------- | ------------ |
| Coverage                   |      ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85`                                                               | Да           |
| mypy errors                |         0 | `mypy src/bioetl --strict`                                                                                  | Да           |
| Циклические импорты        |         0 | `python -c 'import bioetl.domain; import bioetl.application; import bioetl.infrastructure'` + import-linter | Да           |
| Нарушения слоёв            |         0 | import-linter contract + `rg` fallback rules                                                                | Да           |
| `print()` в коде           |         0 | `rg 'print\(' src/bioetl --glob '*.py'`                                                                     | Да           |
| Hardcoded secrets literals |         0 | `gitleaks detect --no-git` (или экв.)                                                                       | Да           |
| Architecture tests         | 100% pass | `pytest tests/test_architecture.py -q`                                                                      | Да           |

## Verification Log (команды)

- `./.venv/bin/python -m mypy src/bioetl --strict 2>&1 | tee /tmp/mypy.out`
- `grep -c 'error:' /tmp/mypy.out`
- `./.venv/bin/python -c 'import bioetl.domain; print("pass")'`
- `rg '^class ' src --glob '*.py' | wc -l`
- `find src -name '*.py' | wc -l`
- `rg -n -e 'TODO|FIXME|XXX|HACK' src | wc -l`
- `rg 'print\(' src/bioetl --glob '*.py' | wc -l`
- `rg -n -e '(api_key|password|secret)\s*=' src | wc -l`
- `./.venv/bin/python -m pytest tests/test_architecture.py -q`
- `timeout 180 ./.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term`
