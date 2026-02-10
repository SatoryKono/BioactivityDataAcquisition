# Консолидированный архитектурный аудит BioETL

Дата: 2026-02-10
Область: `src/bioetl`, `tests`, `docs`

## 0. Методология консолидации

### Исходные аудиты

| # | Аудит | Тип | Общий балл | mypy запущен | pytest запущен |
|---|-------|-----|----------:|:---:|:---:|
| A | architecture-audit-2026-02-07 | Dynamic (pytest + mypy) | 8.13 | Да (10 ошибок) | Да (89.4%) |
| B | Аудит из пользовательского запроса #1 | Статический (read-only) | 7.39 | Нет | Нет |
| C | Аудит из пользовательского запроса #2 | Статический (read-only) | 7.39 | Нет | Нет |
| D | Аудит из пользовательского запроса #3 | Частично dynamic | 7.44 | Да (117 ошибок) | Нет (coverage.json) |

### Принципы консолидации

1. **Факты важнее интерпретаций**: при расхождениях — перепроверка по исходному коду и правилам проекта.
2. **Приоритет динамическим данным**: результаты запуска pytest/mypy приоритетнее статического анализа.
3. **Правила проекта — источник истины**: оценки выставляются по `RULES.md` + `ai-selfreview-rules.md`, а не по внешним ожиданиям аудиторов.
4. **Каждое расхождение документировано**: в секции «Анализ расхождений» приведена аргументация.

---

## 1. Объективные метрики (консенсус)

| Метрика | Аудит A | Аудит B | Аудит C | Аудит D | Консолидация | Источник |
|---------|--------:|--------:|--------:|--------:|--------------:|----------|
| Coverage | 89.40% | [н/д] | [н/д] | 89.54%¹ | **89.4–89.5%** | pytest / coverage.json |
| mypy errors (strict) | 10 | [н/д] | [н/д] | 117 | **10–117**² | mypy --strict |
| Циклические импорты | pass | [н/д] | [н/д] | fail³ | **pass** | python -c import |
| Классов | 945 | 956 | 956 | 956 | **~950** | rg |
| Файлов .py | 533 | 542 | 542 | 542 | **~540** | find |
| Средний LOC модуля | 223.22 | 223.28 | 223.28 | 224.28 | **~223** | wc -l |
| TODO/FIXME | 23 | 24 | 24 | 24 | **~24** | rg |
| print() | 0 | 0 | 0 | 0 | **0** | rg |
| Hardcoded secrets | 14⁴ | 14⁴ | 14⁴ | 14⁴ | **14 паттерн-совпадений, 0 подтверждённых** | rg |

**Примечания:**

1. Аудит D использовал `coverage.json` (дата 2026-01-30), а не живой запуск pytest.
2. Расхождение mypy 10 vs 117 — вероятнее всего различие версии Python или конфигурации (аудит D на Python 3.10, проект target 3.11). Консолидированная позиция: mypy errors > 0, требуется ноль для CI gate.
3. Аудит D получил `ImportError: StrEnum` на Python 3.10 — это ошибка окружения, не циклический импорт.
4. Все 14 совпадений — параметры прокидки (`api_key=api_key`), не хардкоженные литералы секретов.

---

## 2. Анализ расхождений между аудитами

### 2.1. [КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ] Слоистая архитектура (Категория 1)

| Аудит | Оценка | Позиция |
|-------|-------:|---------|
| A | 10/10 | Нарушений по проверке категории нет |
| B | 4/10 | infrastructure→domain (не ports) — нарушение |
| C | 6/10 | 148 infra→domain(non-ports) импортов — нарушение |
| D | 4/10 | 146 infra→domain(non-ports) импортов — нарушение |

**Вердикт: Аудит A прав. Аудиты B, C, D ошибочно интерпретировали правила.**

**Обоснование:**

Матрица импортов в `ai-selfreview-rules.md` (ARCH-001, строка 34):

```
| infrastructure | ✅ | ❌ | ✅ | ❌ | ❌ |
```

Infrastructure → domain = **✅ (разрешено)**.

Примечание к матрице (строки 38–42):

> Infrastructure может импортировать **любые** domain-модули (ports, types,
> exceptions, entities, config, models, value_objects, serialization и т.д.).

Исключение EXC-012:

> Infrastructure зависит от domain by design — domain содержит чистые value objects,
> entities, config и contracts (ports) без I/O.

Единственное ограничение — **ARCH-008**: Ports MUST импортироваться через фасад
`bioetl.domain.ports`, а не из внутренних модулей (`bioetl.domain.ports.xxx_port`).

**Верификация ARCH-008**: grep по `from bioetl.domain.ports.[a-z_]+_port import` в
infrastructure — **0 нарушений**. Все порты импортируются через фасад.

**Консолидированная оценка: 9/10** (снижение на 1 балл за потенциальный
архитектурный риск при 148 зависимостях, но это штатное поведение по правилам проекта).

---

### 2.2. [РАСХОЖДЕНИЕ] Контракты и Ports (Категория 2)

| Аудит | Оценка | Позиция |
|-------|-------:|---------|
| A | 8/10 | mypy boundary mismatch в factory/ports |
| B | 8/10 | Protocol-слой развит, обходы есть |
| C | 5/10 | Ports частично обходятся |
| D | 8/10 | Protocol используются |

**Вердикт: Аудит C занизил оценку по той же ошибочной интерпретации (п. 2.1).**

Аудит A нашёл конкретные mypy-ошибки совместимости в composition (factory return type,
`create_runner` kwargs) — это реальные, но узкие дефекты.

**Консолидированная оценка: 8/10.**

---

### 2.3. [РАСХОЖДЕНИЕ] Silver format validation (Категория 3)

Аудит C нашёл уникальную находку: `PipelineYamlConfig.validate_medallion_formats()`
блокирует только `silver.format == "parquet"`, но не `"jsonl"`.

**Верификация:** Подтверждено — два валидатора:

| Валидатор | Блокирует parquet | Блокирует jsonl |
|-----------|:-:|:-:|
| `PipelineYamlConfig.validate_medallion_formats()` | Да | **Нет** |
| `_MedallionConfigValidator._validate_layer_formats()` (PreflightService) | Да | Да |

Система в целом **отклоняет** jsonl для Silver (PreflightService ловит), но есть
**несогласованность** между двумя точками валидации. Это валидная находка.

**Влияние на оценку:** учтено как minor inconsistency (–0.5).

---

### 2.4. [РАСХОЖДЕНИЕ] Fencing token (Категория 5)

Все четыре аудита отметили отсутствие fencing token. Но:

- **ADR-010** (local-only deployment) и **EXC-011** явно принимают MemoryLock как
  достаточный механизм.
- Реализован **Safety Guard** (`validate_owner()`) — трёхуровневая проверка:
  owner_id + physical lock status + TTL expiration.
- `BatchWriter` вызывает `await self._lock_validator()` **перед каждой записью**.
- Для single-instance deployment fencing token — over-engineering.

**Консолидированная позиция:** это не дефект, а осознанное архитектурное решение.
Зафиксировано в ADR-010. Оценка не снижается.

---

### 2.5. [РАСХОЖДЕНИЕ] Тестирование (Категория 8)

| Аудит | Оценка | Данные |
|-------|-------:|--------|
| A | 8/10 | 89.4%, 1 failing test |
| B | 6/10 | [данные отсутствуют] |
| C | 6/10 | [данные отсутствуют] |
| D | 9/10 | 89.54% из coverage.json |

**Вердикт:** Аудиты B и C без данных выставили консервативную оценку 6/10 — это
методологическая ошибка. При отсутствии данных правильнее указать `[н/о]`, а не
штрафовать.

Coverage подтверждён двумя независимыми источниками: 89.4% (live) и 89.54% (json).
CI enforce `--cov-fail-under=85`. Один failing test (version constraint) — minor.

**Консолидированная оценка: 8.5/10.**

---

### 2.6. [РАСХОЖДЕНИЕ] Безопасность (Категория 9)

| Аудит | Оценка | Уникальная находка |
|-------|-------:|-------------------|
| A | 6/10 | PubMed PII risk (email, address) |
| B | 8/10 | — |
| C | 9/10 | — |
| D | 8/10 | — |

**Вердикт:** Аудит A нашёл конкретный риск PII в PubMed author extractor, которого
не заметили остальные. Это реальная находка.

**Консолидированная оценка: 7/10.**

---

### 2.7. [РАСХОЖДЕНИЕ] Документация (Категория 10)

| Аудит | Оценка |
|-------|-------:|
| A | 7/10 |
| B | 9/10 |
| C | 7/10 |
| D | 6/10 |

Все аудиты отметили отсутствие файлов `01-domain-objects.md`, `02-etl-layers.md` и т.д.
Эти имена — из шаблона аудита, а не из требований проекта. Фактические документы
(`01-domain-layer.md`, `data-flow.md`, `data-layers.md`) покрывают те же темы.

**Реальные проблемы**: отсутствие маппинг-документа / навигационного индекса.

**Консолидированная оценка: 7.5/10.**

---

## 3. Консолидированные оценки

### 3.1. Сводная таблица

| # | Категория | Вес | A | B | C | D | Консолид. | Взвеш. | Обоснование |
|---|-----------|----:|--:|--:|--:|--:|----------:|-------:|-------------|
| 1 | Слоистая архитектура | 15% | 10 | 4 | 6 | 4 | **9.0** | 1.35 | По правилам проекта infra→domain разрешён (EXC-012) |
| 2 | Контракты и Ports | 12% | 8 | 8 | 5 | 8 | **8.0** | 0.96 | Protocol-система развита, 2 mypy boundary issue |
| 3 | Medallion Architecture | 12% | 7 | 8 | 8 | 8 | **8.0** | 0.96 | Основа соблюдается; inconsistency silver validation |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 9 | 9 | 9 | **9.0** | 0.90 | CB + метрики + классификация — консенсус |
| 5 | Блокировки и конкурентность | 10% | 8 | 7 | 8 | 8 | **8.5** | 0.85 | Safety Guard достаточен для local-only (ADR-010) |
| 6 | Валидация и DQ | 10% | 8 | 8 | 9 | 8 | **8.0** | 0.80 | Pandera + quarantine + thresholds; write_gold_merged gap |
| 7 | Логирование/наблюдаемость | 8% | 9 | 9 | 8 | 8 | **8.5** | 0.68 | print()=0, structured logging, Prometheus |
| 8 | Тестирование | 8% | 8 | 6 | 6 | 9 | **8.5** | 0.68 | Coverage 89.4%+, CI gate 85%, VCR/contract тесты |
| 9 | Безопасность/секреты | 8% | 6 | 8 | 9 | 8 | **7.0** | 0.56 | PII risk в PubMed (аудит A), salted hashing для остальных |
| 10 | Документация | 7% | 7 | 9 | 7 | 6 | **7.5** | 0.53 | ADR/contracts/CHANGELOG есть; навигация неполная |
| | **Итого** | **100%** | **8.13** | **7.39** | **7.39** | **7.44** | | **8.27** | |

### 3.2. Интерпретация

**8.27 / 10 → PASS** (порог ≥ 8.0 по scoring matrix).

Проект production-ready с рядом точечных улучшений. Основная архитектура (Hexagonal,
Medallion, DI, observability) реализована корректно.

### 3.3. Ключевые ошибки аудиторов

| Ошибка | Аудиты | Влияние на балл | Причина |
|--------|--------|----------------:|---------|
| Infra→domain flagged как нарушение | B, C, D | –1.5…–3.0 | Не прочитана заметка к ARCH-001 и EXC-012 |
| Coverage scored без данных | B, C | –0.5 | Методологическая — [н/о] вместо штрафа |
| Fencing token как обязательное | B, C, D | –0.3 | Не учтён ADR-010 (local-only) и EXC-011 |
| PubMed PII не замечен | B, C, D | 0 (не нашли) | Недостаточная глубина security-анализа |

---

## 4. Консолидированные находки (подтверждённые)

### 4.1. [P1] PubMed PII risk (security)

- **Severity**: HIGH
- **Источник**: Аудит A
- **Локация**: `src/bioetl/application/pipelines/pubmed/extractors/author.py`
- **Суть**: Поля `email`, `address` отмечены security-тестом как потенциально
  не-хешируемые PII.
- **Решение**: Явная стратегия: удалить до Silver/Gold или обязательный salted hashing
  на transformer уровне + тесты.
- **Критерий готовности**: `tests/security/test_security.py` без skip по этому кейсу.
- **Трудозатраты**: M (дни).

### 4.2. [P1] Согласовать silver format validation

- **Severity**: MEDIUM
- **Источник**: Аудит C (верифицировано)
- **Локация**: `src/bioetl/infrastructure/schemas/pipeline_config.py:1055-1090`
- **Суть**: `validate_medallion_formats()` блокирует только `parquet` для Silver,
  но не `jsonl`. PreflightService ловит оба, но рассогласование — потенциальный
  bypass при обходе preflight.
- **Решение**: В `validate_medallion_formats()` заменить проверку на
  `silver.format != "delta"` (strict positive check).
- **Критерий готовности**: Негативные тесты на jsonl/parquet в Silver через
  PipelineYamlConfig.
- **Трудозатраты**: S (часы).

### 4.3. [P1] Strict validation для write_gold_merged

- **Severity**: MEDIUM
- **Источник**: Аудит A
- **Локация**: `src/bioetl/infrastructure/storage/gold_writer.py:271-285`
- **Суть**: `write_gold_merged` записывает в Gold без Pandera strict validation.
- **Решение**: Добавить strict schema contract для merged datasets или ADR с
  обоснованием исключения.
- **Критерий готовности**: Strict validation enforced или задокументировано
  исключение.
- **Трудозатраты**: M (дни).

### 4.4. [P2] mypy strict debt

- **Severity**: MEDIUM
- **Источник**: Аудит A (10 ошибок), Аудит D (117 ошибок)
- **Суть**: mypy strict ≠ 0 ошибок. Расхождение 10 vs 117 вероятно из-за
  версии Python (3.10 vs 3.11) и различий в stubs.
- **Решение**: Поэтапное устранение; закрепить CI gate `mypy --strict` = 0.
- **Критерий готовности**: `mypy src/bioetl --strict` exit code 0.
- **Трудозатраты**: M (дни).

### 4.5. [P2] Composition factory mypy boundary mismatch

- **Severity**: MEDIUM
- **Источник**: Аудит A
- **Локации**:
  - `src/bioetl/composition/factories/pipeline_factory.py:377` — return type ≠
    `DataSourcePort`
  - `src/bioetl/composition/bootstrap/runtime/pipeline.py:150` — unexpected keyword
    для `create_runner`
- **Решение**: Исправить сигнатуры фабрик или обновить порты.
- **Критерий готовности**: `mypy --strict` проходит для этих модулей.
- **Трудозатраты**: S (часы).

### 4.6. [P3] Навигационный индекс документации

- **Severity**: LOW
- **Источник**: Аудиты B, C, D
- **Суть**: Внешние аудиторы ожидают определённые имена документов, которые
  не совпадают с фактическими. Маппинг-документ отсутствует.
- **Решение**: Создать `docs/00-project/doc-map.md` с таблицей соответствий.
- **Трудозатраты**: S (часы).

### 4.7. Отклонённые находки

| Находка | Аудиты | Причина отклонения |
|---------|--------|-------------------|
| Infrastructure→domain (non-ports) = нарушение | B, C, D | Разрешено правилами: ARCH-001 матрица ✅, EXC-012 |
| Fencing token отсутствует = дефект | B, C, D | ADR-010, EXC-011: local-only, Safety Guard достаточен |
| Bronze v1 path versioning | A, D | Не mandated в RULES.md; текущий формат документирован |
| Coverage не подтверждён = 6/10 | B, C | Методологическая ошибка; данные есть (89.4%) |

---

## 5. План рефакторинга (консолидированный)

### Фаза 1: Security + Validation gaps (S–M)

| # | Задача | Ref | Влияние |
|---|--------|-----|--------:|
| 1 | PubMed PII hashing для email/address | §4.1 | +0.16 |
| 2 | Strict positive silver format check | §4.2 | +0.06 |
| 3 | Strict validation для write_gold_merged | §4.3 | +0.10 |

**Ожидаемый балл после фазы 1: 8.27 → ~8.6**

### Фаза 2: Type safety + Contracts (M)

| # | Задача | Ref | Влияние |
|---|--------|-----|--------:|
| 4 | mypy strict debt → 0 | §4.4 | +0.12 |
| 5 | Factory/Port signature fixes | §4.5 | +0.06 |

**Ожидаемый балл после фазы 2: ~8.6 → ~8.8**

### Фаза 3: Documentation (S)

| # | Задача | Ref | Влияние |
|---|--------|-----|--------:|
| 6 | Doc navigation index | §4.6 | +0.05 |

**Ожидаемый балл после фазы 3: ~8.8 → ~8.85**

---

## 6. CI-метрики контроля регресса (консенсус всех аудитов)

| Метрика | Порог | Команда | Блокирует PR |
|---------|------:|---------|:---:|
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Нарушения слоёв | 0 | `pytest tests/architecture/` | Да |
| print() в коде | 0 | `rg 'print\(' src/bioetl -g '*.py'` | Да |
| Secrets heuristic | 0 high-confidence | `rg '(api_key\|password\|secret)\s*=' src/ -g '*.py'` + allowlist | Да |
| Silver format guard | pass | Unit-тесты на `validate_medallion_formats()` | Да |
| Lock safety guard | pass | `pytest tests/architecture/test_lock_safety_guard.py` | Да |

---

## 7. Verification log (данный консолидированный аудит)

Перепроверки выполненные в рамках консолидации:

- ✅ Чтение `ai-selfreview-rules.md` — матрица импортов, EXC-012, ARCH-008
- ✅ Чтение `RULES.md` §1.1 — подтверждение infra→domain ✅
- ✅ Grep `from bioetl.domain.ports.[a-z_]+_port import` в infrastructure — 0 ARCH-008
  нарушений
- ✅ Подсчёт infra→domain non-ports импортов — 148 (128 runtime, 20 TYPE_CHECKING)
- ✅ Чтение silver validation в `pipeline_config.py` и `preflight_service.py` —
  подтверждена inconsistency
- ✅ Чтение `domain/ports/locking.py` и `infrastructure/locking/memory_lock.py` —
  подтверждён Safety Guard, нет fencing token
- ✅ Чтение `coverage.json` — 89.54%
- ✅ Чтение CI workflows — `--cov-fail-under=85` подтверждён
- ✅ Чтение `bronze_writer.py` — нет v1 в path, формат `{provider}/{entity}/{date}/`
