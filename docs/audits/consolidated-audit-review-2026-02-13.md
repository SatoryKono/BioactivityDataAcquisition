# Консолидированный обзор аудитов и скорректированный план рефакторинга

Дата: 2026-02-13
Область: Анализ четырёх параллельных аудитов BioETL из веток `codex/conduct-architectural-audit-for-bioetl*`

---

## 1. Исходные данные

Проанализированы четыре параллельных аудита из веток:

| # | Ветка | Коммит | Итоговый балл |
|---|-------|--------|---------------|
| B1 | `codex/conduct-architectural-audit-for-bioetl` | `5b767f1` | **7.97/10** |
| B2 | `codex/conduct-architectural-audit-for-bioetl-t4pr4g` | `df9ada4` | **7.10/10** |
| B3 | `codex/conduct-architectural-audit-for-bioetl-bjpj6f` | `79ab301` | **8.24/10** |
| B4 | `codex/conduct-architectural-audit-for-bioetl-267bw6` | `b2ddd80` | **8.74/10** |

Разброс итогового балла: **1.64 балла** (от 7.10 до 8.74) — это существенное расхождение для одной и той же кодовой базы.

---

## 2. Выявленные неточности и ошибки

### 2.1. КРИТИЧЕСКАЯ ОШИБКА: Оценка «Слоистая архитектура»

| Ветка | Оценка | Вердикт |
|-------|--------|---------|
| B1 | **9/10** | «Прямых нарушений не найдено» |
| B2 | **4/10** | «97 импортов infra→domain(non-ports) — нарушение» |
| B3 | **9.5/10** | «Нарушений импорт-границ не найдено» |
| B4 | **10/10** | «Нарушений импорт-границ не найдено» |

**Факт:** В `infrastructure/` обнаружено **143 импорта** из `domain.*` (non-ports) в 56 файлах. Однако это **НЕ нарушение**.

**Обоснование:**
- ARCH-001 матрица: `infrastructure → domain` = ✅ (разрешено)
- Примечание к ARCH-001: *«Infrastructure может импортировать любые domain-модули (ports, types, exceptions, entities, config, models, value_objects, serialization и т.д.)»*
- EXC-012: Явно декларирует infrastructure → domain.entities/config/types/exceptions как допустимые
- EXC-013: domain.types и domain.exceptions разрешены **везде**

**Вердикт:**
- **B2 (4/10) — ГРУБАЯ ОШИБКА.** Спутал допустимую архитектурную зависимость с нарушением. Занизил оценку на 5 баллов.
- **B1 (9/10) — корректно**, но с оговоркой «может трактоваться как нарушение», что вносит путаницу.
- **B3 (9.5/10) и B4 (10/10) — корректны.** 10 — наиболее точная оценка.

**Скорректированная оценка: 10/10**

---

### 2.2. ОШИБКА: Оценка «Контракты и Ports»

| Ветка | Оценка | Обоснование |
|-------|--------|-------------|
| B1 | **6/10** | «97 импортов non-port → нарушение» |
| B2 | **6/10** | «Ports есть, но не единственная граница» |
| B3 | **9/10** | «37 Protocol, но 39 mypy ошибок» |
| B4 | **9/10** | «Protocol-first, реализации в infrastructure» |

**Факт:**
- 38 Protocol-классов определены в `domain/ports/` — полноценная port-архитектура
- 79 импортов через `domain.ports` фасад из infrastructure — корректная зависимость
- 143 импорта domain non-ports — допустимы по EXC-012
- mypy ошибки (39 шт.) — проблема типизации, НЕ контрактов

**Вердикт:**
- **B1 и B2 (6/10) — занижено.** Основание (non-port imports как нарушение) ошибочно.
- **B3 и B4 (9/10) — корректны.**

**Скорректированная оценка: 9/10**

---

### 2.3. ОШИБКА: Подсчёт протоколов

| Ветка | Заявлено |
|-------|----------|
| B1 | не указано точно |
| B2 | «минимум 38 объявлений» |
| B3 | «37 Protocol» |
| B4 | не указано точно |

**Факт: 38 Protocol-классов** в `domain/ports/`. B3 ошибся на 1.

---

### 2.4. ОШИБКА: Content hash алгоритм

| Ветка | Заявление |
|-------|-----------|
| B1 | Не указан конкретный алгоритм |
| B2 | «sha256(provider + canonical_json)» |
| B3 | «Content hash реализован канонически» |
| B4 | «SHA256 content hash with canonical JSON normalization» |

**Факт: Используются ДВА разных хэша:**
- **Content hash для версионирования записей:** `SHA256` (`domain/transformations.py:119`)
  - Формула: `sha256(provider + canonical_json(record))`
- **Checksum для целостности Bronze-файлов:** `BLAKE2b` (`infrastructure/storage/bronze_writer.py`)
  - Поле: `BronzeWriteResult.checksum_blake2`

Аудиты не разделили эти два разных применения. Для полноты картины:
- PII hashing использует `SHA256 + salt` (`domain/services/data_normalization_service.py:114`)
- Cache-ключи резильентности: `MD5` (`domain/resilience.py:102`, с `usedforsecurity=False`)

---

### 2.5. ОШИБКА: Покрытие тестами

| Ветка | Заявление | Метод |
|-------|-----------|-------|
| B1 | «89.54%» | Из `coverage.json` |
| B2 | «[данные отсутствуют]» | Запуск прерван (pandas missing) |
| B3 | «[данные отсутствуют]» | Запуск прерван |
| B4 | «89.54%» | Из `coverage.json` |

**Факт:** `coverage.json` существует и содержит 89.54%. Однако это **артефакт предыдущего запуска**, а не результат текущего аудита. Ни один из четырёх аудитов не смог запустить `pytest --cov` в текущем окружении из-за отсутствия зависимостей (pandas/pandera).

**Вердикт:** B1 и B4 выдают артефактное значение за подтверждённое. B2 и B3 честно указывают «данные отсутствуют» — это корректнее. Правильная оценка: **89.54% (из артефакта, не подтверждено текущим запуском)**.

---

### 2.6. ОШИБКА: Циклические импорты

| Ветка | Заявление |
|-------|-----------|
| B1 | «fail (pandera ModuleNotFoundError)» |
| B2 | «fail (pandera ModuleNotFoundError)» |
| B3 | «pass» |
| B4 | «pass» |

**Факт:** Команда `from bioetl.domain import *` падает с `ModuleNotFoundError: pandera`. Это **не циклический импорт**, а отсутствие зависимости в окружении. B1/B2 путают причину, B3/B4 вероятно имели pandera установленным.

**Скорректированный вердикт:** Циклических импортов не выявлено. Тест инконклюзивен из-за окружения.

---

### 2.7. ОШИБКА: TODO/FIXME подсчёт

Все четыре ветки указывают **23 шт**. Однако при ручной проверке **все 23 — ложноположительные срабатывания** на подстроку `XXX` в InChI-ключах, ORCID-шаблонах, DOI-паттернах и `CHEMBLXXX`.

**Реальное значение: 0 TODO/FIXME/HACK** в production-коде.

---

### 2.8. ОШИБКА: Средний размер модуля

| Ветка | Значение |
|-------|----------|
| B1 | 223.38 строк |
| B2-B4 | 222.38 строк |

Расхождение незначительно (вероятно, разный набор файлов в подсчёте). Не влияет на выводы.

---

### 2.9. ОШИБКА: Hardcoded secrets

Все ветки: **14 срабатываний**. Однако все 14 — легитимный код (передача параметров, чтение из конфигов). **0 реальных hardcoded секретов**.

---

### 2.10. ОШИБКА B1: Предложение «вынести из domain в adapter-local DTO»

B1 предлагает *«оставить в domain только Protocol/VO/DTO-контракты, вынести infra-specific маппинг/типы в adapter-local DTO»* для «нормализации import-границ».

**Это ошибочная рекомендация.** ARCH-001 + EXC-012 явно разрешают infrastructure → domain для всех типов (entities, config, types, exceptions, value_objects). Вынесение их в adapter-local DTO:
- Нарушит DRY (дублирование типов)
- Создаст маппинг-слой без добавленной ценности
- Противоречит правилам проекта

---

### 2.11. ОШИБКА B2: Предложение «Medallion path-contract v1»

B2 предлагает *«добавить версионированный path-builder (bronze/v1/...)»*. Текущий формат `{provider}/{entity}/{date}/...` — это осознанный выбор. Нет документального требования на `v1` prefix, и его добавление ломает обратную совместимость с данными.

**Это спорная рекомендация без обоснования из RULES.md или ADR.**

---

### 2.12. ОШИБКА B3: Документация «5 ключевых документов отсутствуют»

Все ветки отмечают отсутствие `01-domain-objects.md` ... `05-physical-layout.md`. Однако эти имена были **частью промпта аудита**, а не реальными требованиями проекта. Снижение оценки документации за отсутствие несуществующих документов некорректно.

---

## 3. Скорректированная сводная таблица

| # | Категория | Вес | B1 | B2 | B3 | B4 | **Скорр.** | Обоснование |
|---|-----------|----:|---:|---:|---:|---:|---:|-------------|
| 1 | Слоистая архитектура | 15% | 9 | 4 | 9.5 | 10 | **10** | 0 нарушений; EXC-012 покрывает infra→domain |
| 2 | Контракты и Ports | 12% | 6 | 6 | 9 | 9 | **9** | 38 Protocol, ports-first design |
| 3 | Medallion Architecture | 12% | 9 | 8 | 9 | 9 | **9** | Bronze JSONL+zstd, Silver Delta, Gold strict |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 9 | 8.5 | 9 | **9** | CB threshold=5, timeout=300, metrics |
| 5 | Блокировки и конкурентность | 10% | 8 | 8 | 8.5 | 9 | **8.5** | MemoryLock+TTL+heartbeat+safety; fencing неявен |
| 6 | Валидация и DQ | 10% | 8 | 8 | 8 | 8 | **8** | Thresholds 5/20, Quarantine; NoOp допускается |
| 7 | Логирование и observability | 8% | 9 | 9 | 8.5 | 9 | **9** | UnifiedLogger+Prometheus, print=0 |
| 8 | Тестирование | 8% | 6 | 5 | 6 | 7 | **6.5** | coverage 89.54% (артефакт); formatting fails; mypy 39 |
| 9 | Безопасность и секреты | 8% | 7 | 8 | 7.5 | 8 | **8** | 0 реальных hardcoded; SecretStr+salted |
| 10 | Документация | 7% | 8 | 8 | 5.5 | 8 | **8** | ADR/RULES актуальны; «missing docs» — ложная находка |

### Скорректированный итоговый балл

| # | Категория | Вес | Оценка | Взвеш. |
|---|-----------|----:|-------:|-------:|
| 1 | Слоистая архитектура | 15% | 10 | 1.50 |
| 2 | Контракты и Ports | 12% | 9 | 1.08 |
| 3 | Medallion Architecture | 12% | 9 | 1.08 |
| 4 | Ошибки и Circuit Breaker | 10% | 9 | 0.90 |
| 5 | Блокировки и конкурентность | 10% | 8.5 | 0.85 |
| 6 | Валидация и DQ | 10% | 8 | 0.80 |
| 7 | Логирование и observability | 8% | 9 | 0.72 |
| 8 | Тестирование | 8% | 6.5 | 0.52 |
| 9 | Безопасность и секреты | 8% | 8 | 0.64 |
| 10 | Документация | 7% | 8 | 0.56 |
| **Итого** | | **100%** | | **8.65** |

**8.65/10** — Production-ready с минорными улучшениями. Ближе всего к B4 (8.74), B1 и B3 допустили ошибки средней тяжести, B2 — критическую.

---

## 4. Скорректированный консолидированный план рефакторинга

На основе верифицированных фактов, а не ошибочных выводов аудитов.

### ~~УДАЛЕНО: «Нормализовать import-границы infrastructure ↔ domain»~~

Предложено в: B1, B2.
**Причина удаления:** Ложноположительное обнаружение. Infrastructure → domain импорты — штатная архитектурная зависимость по ARCH-001 + EXC-012. Никакой рефакторинг не требуется.

### ~~УДАЛЕНО: «Medallion path-contract v1»~~

Предложено в: B2.
**Причина удаления:** Текущий формат соответствует реализации. Нет требования на `v1` prefix. Изменение ломает обратную совместимость без обоснования.

---

### [P1] Исправить formatting gates (ruff format/isort)

**Источник:** B1, B2, B3, B4 (все четыре ветки согласны).
**Категория:** Тестирование (8).
**Текущий балл → Целевой:** 6.5 → 8.

**Проблема:**
- `tests/architecture/test_code_formatting.py` падает на ruff format и isort проверках.
- Минимум затронуты: `src/bioetl/__init__.py`, `src/bioetl/infrastructure/adapters/pubmed/_fetch.py`, `src/bioetl/infrastructure/storage/gold_writer.py`.

**Решение:**
1. `ruff format src/ tests/`
2. `ruff check --fix --select I src/ tests/` (isort)
3. Проверить `pytest tests/architecture/test_code_formatting.py`

**Критерий готовности:** Тест `test_code_formatting.py` зелёный.
**Риски:** Минимальные (только форматирование). Большой diff, но без изменения логики.
**Файлы:** Все `.py` файлы, затронутые auto-format.

---

### [P1] Закрыть mypy --strict до 0 ошибок

**Источник:** B1, B2, B3, B4 (все согласны; 39 ошибок в 17 файлах).
**Категория:** Типизация (TYPE), Тестирование (8).
**Текущий балл → Целевой:** 6.5 → 8.5.

**Проблема:**
39 ошибок mypy --strict в 17 из 513 файлов. Основные типы ошибок:
- `redundant-cast` в трансформерах (ChEMBL, OpenAlex, CrossRef)
- `arg-type` несовместимости в composition/factories и preflight
- `type-arg` проблемы с Pandera DataFrameModel в UniProt-схемах

**Решение по типам ошибок:**
1. **redundant-cast** (самая частая): Удалить ненужные `cast()` вызовы.
2. **arg-type** (composition/factories): Исправить сигнатуры factory-методов для соответствия портам.
3. **type-arg** (Pandera/UniProt): Добавить type: ignore[type-arg] с комментарием для DataFrameModel (known Pandera typing limitation) или использовать pandera-stubs если доступны.

**Ключевые файлы:**
- `src/bioetl/application/pipelines/chembl/transformer.py` (redundant-cast)
- `src/bioetl/application/pipelines/openalex/transformer.py` (redundant-cast)
- `src/bioetl/application/pipelines/crossref/transformer.py` (redundant-cast)
- `src/bioetl/composition/bootstrap/cli/config.py` (arg-type)
- `src/bioetl/composition/factories/services_factory.py` (arg-type)
- `src/bioetl/application/core/preflight_service.py` (arg-type)
- `src/bioetl/domain/schemas/uniprot/*.py` (type-arg DataFrameModel)

**Критерий готовности:** `mypy src/bioetl --strict` = 0 ошибок.
**Риски:** Изменение сигнатур может вызвать каскадные правки. Pandera typing stubs могут быть неполными.

---

### [P2] Обеспечить воспроизводимость quality gates в CI-окружении

**Источник:** B2 (не смог запустить coverage), B3 (не смог запустить coverage).
**Категория:** Тестирование (8).

**Проблема:**
Два из четырёх аудитов не смогли получить coverage из-за отсутствия runtime-зависимостей (pandas, pandera) в окружении. Это означает, что CI-пайплайн или dev-bootstrap может быть неполным.

**Решение:**
1. Убедиться что `pyproject.toml` / `requirements-dev.txt` содержит все зависимости для тестов.
2. Добавить smoke-check зависимостей как первый шаг CI.
3. Задокументировать минимальное dev-окружение.

**Критерий готовности:** `pytest --cov=src/bioetl --cov-fail-under=85` стабильно проходит в CI.
**Риски:** Увеличение размера CI-образа.

---

### [P2] Ужесточить валидацию: устранить NoOp-обходы для Gold/Silver

**Источник:** B4 (единственный, кто обнаружил).
**Категория:** Валидация и DQ (6).
**Текущий балл → Целевой:** 8 → 9.

**Проблема:**
- `NoOpSilverValidator` и `NoOpGoldValidator` позволяют обходить Pandera-валидацию
- `strict=False` по умолчанию в `BasePanderaValidator`
- В production-пайплайнах это снижает гарантии DQ

**Решение:**
1. Для production-пайплайнов: composition factories **MUST** инжектировать реальные валидаторы (не NoOp).
2. Добавить архитектурный тест: в `composition/factories/` не должно быть `NoOpValidator` для Gold/Silver.
3. Рассмотреть `strict=True` по умолчанию для Gold-валидатора.

**Файлы:**
- `src/bioetl/infrastructure/validation/pandera_validator.py`
- `src/bioetl/composition/factories/services_factory.py` (или аналог)

**Критерий готовности:** Архитектурный тест запрещает NoOp для production. Gold-валидация всегда strict.
**Риски:** Исторические данные могут не проходить strict-валидацию. Нужен fallback/migration plan.

---

### [P3] Добавить точный детектор секретов в CI

**Источник:** B1, B2, B3, B4 (все отмечают шум regex-проверки).
**Категория:** Безопасность (9).
**Текущий балл → Целевой:** 8 → 9.

**Проблема:**
14 regex-срабатываний на `api_key|password|secret` — все ложноположительные, но нет автоматического способа отличить реальный hardcoded secret от параметра.

**Решение:**
1. Добавить `detect-secrets` или `gitleaks` в pre-commit/CI.
2. Создать `.secrets.baseline` с allowlist для легитимных паттернов.
3. Заменить grep-based проверку на AST-aware scanner.

**Критерий готовности:** 0 high-severity findings; документированный allowlist.
**Риски:** Ложные срабатывания на старте (решается через baseline).

---

### [P3] Явный fencing token API для LockPort

**Источник:** B1, B3 (оба заметили).
**Категория:** Блокировки и конкурентность (5).
**Текущий балл → Целевой:** 8.5 → 9.

**Проблема:**
Safety guard реализован через `validate_owner(key, owner_id)`, но нет явного fencing token как отдельной абстракции. Роль fencing выполняет `owner_id`, что функционально достаточно для local-only deployment (ADR-010), но не формализовано в контракте.

**Решение:**
1. Расширить `LockPort.acquire()` чтобы возвращал `FencingToken` value object.
2. Storage writers проверяют token перед записью.
3. Для MemoryLock — trivial implementation поверх `owner_id`.

**Файлы:**
- `src/bioetl/domain/ports/locking.py`
- `src/bioetl/infrastructure/locking/memory_lock.py`
- Storage writers

**Критерий готовности:** Fencing token в API LockPort + тест на owner validation.
**Риски:** Breaking change в LockPort. Требуется обновление всех callers.

---

## 5. Roadmap

### Фаза 1: Quality Gates (P1)

| Задача | Влияние на балл | Сложность |
|--------|----------------|-----------|
| ruff format + isort | Тестирование 6.5→7.5 | S |
| mypy --strict → 0 | Тестирование 7.5→8.5 | M |

**Ожидаемый балл после Фазы 1: 8.65 → 9.15**

### Фаза 2: Валидация и CI (P2)

| Задача | Влияние на балл | Сложность |
|--------|----------------|-----------|
| CI reproducibility | Тестирование стабилизация | S-M |
| Strict validation для Gold/Silver | Валидация 8→9 | M |

**Ожидаемый балл после Фазы 2: 9.15 → 9.35**

### Фаза 3: Hardening (P3)

| Задача | Влияние на балл | Сложность |
|--------|----------------|-----------|
| Secret scanner | Безопасность 8→9 | S |
| Fencing token API | Блокировки 8.5→9 | M |

**Ожидаемый балл после Фазы 3: 9.35 → 9.55**

---

## 6. Метрики контроля регресса (CI)

| Метрика | Порог | Команда | Блокирует PR |
|---------|-------|---------|-------------|
| Coverage | ≥85% | `pytest --cov=src/bioetl --cov-fail-under=85` | Да |
| mypy errors | 0 | `mypy src/bioetl --strict` | Да |
| Formatting | 0 | `ruff format --check src tests && ruff check --select I src tests` | Да |
| Layer violations | 0 | `pytest tests/architecture/test_layer_dependencies.py` | Да |
| print() | 0 | `rg 'print\(' src/bioetl -g '*.py'` | Да |
| Secrets | 0 high | `detect-secrets scan --baseline .secrets.baseline` | Да |

---

## 7. Ключевые выводы

1. **Архитектура solid.** Ни одного нарушения import-границ (ARCH-001). B2 критически ошибся, засчитав допустимые infra→domain зависимости за нарушения.

2. **Основной долг — typing и formatting.** 39 ошибок mypy + падающие formatting тесты — единственные реальные блокеры.

3. **Рефакторинг import-границ НЕ нужен.** Предложения B1/B2 по «нормализации» infra→domain импортов противоречат RULES.md (ARCH-001 + EXC-012) и создадут регрессию.

4. **NoOp-валидаторы — архитектурный риск.** Только B4 заметил, что `NoOpValidator` + `strict=False` подрывает гарантии DQ. Это требует внимания.

5. **Coverage подтверждён артефактно (89.54%)**, но текущий запуск ни один аудит не смог выполнить. CI воспроизводимость требует улучшения.
