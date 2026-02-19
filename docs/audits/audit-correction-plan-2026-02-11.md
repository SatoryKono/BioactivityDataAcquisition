# Консолидированный план корректировки по результатам аудита

**Дата:** 2026-02-11
**Scope:** `src/bioetl/` — статическая инвентаризация + targeted QA
**На основе:** 3 отчёта аудита (inventory, architecture audit, targeted QA)
**Валидация:** перекрёстная проверка всех находок с кодовой базой и RULES.md

---

## 1. Критический анализ находок аудита

### 1.1 Отклонённые находки (FALSE POSITIVE)

#### FP-1: Infrastructure → domain imports (заявлено как CRITICAL)

**Вердикт: FALSE POSITIVE — не является нарушением.**

Все три отчёта флагируют 55–146 импортов из `bioetl.domain.*` в `infrastructure/`
как CRITICAL-нарушение. Это **ошибка аудита**, противоречащая собственным правилам проекта:

| Источник правила | Что разрешает |
|------------------|---------------|
| **ARCH-001** (матрица импортов) | infrastructure → domain: **✅** (checkmark в матрице) |
| **EXC-012** (исключение) | Явно перечисляет: ports, entities, types, exceptions, config — всё разрешено |
| **ADR-005** (архитектурное решение) | Подтверждает ту же матрицу: infrastructure → domain ✅ |
| **tests/test-architecture.py** | `test-infrastructure-boundaries` проверяет только infra→app (запрещено), infra→domain **не проверяется как нарушение** |

Примечание к ARCH-001 прямо гласит:
> *«Infrastructure может импортировать **любые** domain-модули (ports, types, exceptions,
> entities, config, models, value-objects, serialization и т.д.)»*

Все 146 импортов попадают в разрешённые категории EXC-012. Архитектурные тесты
подтверждают: запрет действует только на infra→application.

**Действие:** Закрыть как false positive. Инструкции аудита скорректировать —
ссылаться на ARCH-001/EXC-012/ADR-005 как на авторитетные правила границ.

---

#### FP-2: GoldFiltersConfig.to-domain дублирование (заявлено как HIGH)

**Вердикт: FALSE POSITIVE — намеренный архитектурный паттерн.**

| Файл | Класс | Назначение |
|------|-------|------------|
| `base-schemas.py:551` | `BaseGoldFiltersConfig.to-domain()` | Базовый класс для standalone filter configs |
| `pipeline-config.py:795` | `GoldFiltersConfig.to-domain()` | Независимая реализация для YAML pipeline config |

Два класса **не связаны наследованием** — они обслуживают разные ветки конфигурации
(inline pipeline vs external filter files). `filter-config.py` использует type alias'ы
на base-классы, а `pipeline-config.py` имеет собственную иерархию. Одинаковая логика
конвертации — следствие одинакового целевого domain API, а не copy-paste.

**Действие:** Закрыть как false positive. При необходимости — документировать design
rationale в комментарии.

---

### 1.2 Подтверждённые находки

Ниже — находки, **прошедшие перекрёстную валидацию** с кодовой базой.

---

## 2. Валидированный план корректировки

### FIX-1: Удалить дублирующие pipeline-классы [HIGH]

**Проблема:** Один и тот же пустой класс-наследник `BasePipeline` определён дважды —
в `--init--.py` (используется в production) и в отдельном модуле (не используется).

| Пакет | `--init--.py` (production) | Модуль-дубль (dead) |
|-------|---------------------------|---------------------|
| pubchem | `--init--.py:17` — PubChemCompoundPipeline | `compound.py:11` |
| pubmed | `--init--.py:17` — PubMedPublicationPipeline | `publication.py:12` |
| uniprot | `--init--.py:21` — UniProtProteinPipeline | `protein.py:11` |

**Доказательство:** `compound.py`, `publication.py`, `protein.py` имеют 0 production-импортов.
Все factory/composition imports идут через `--init--.py`.

**Риск бездействия:** Расхождение реализаций при будущих изменениях, ложная сложность
при инвентаризации.

**Корректировка:**
1. Удалить `compound.py`, `publication.py`, `protein.py`
2. Проверить, что тесты, импортирующие напрямую из этих модулей, переключены на import
   из `--init--.py` (package level)
3. Запустить `pytest tests/` для regression-проверки

**Затрагиваемые файлы:**
- `src/bioetl/application/pipelines/pubchem/compound.py` → DELETE
- `src/bioetl/application/pipelines/pubmed/publication.py` → DELETE
- `src/bioetl/application/pipelines/uniprot/protein.py` → DELETE
- Тесты: обновить imports если требуется

---

### FIX-2: Централизовать хеширование publication-term entity ID [HIGH]

**Проблема:** Идентичная логика вычисления entity-id для publication-term
дублируется byte-for-byte в двух местах:

| Файл | Метод | Видимость |
|------|-------|-----------|
| `application/pipelines/chembl/publication-term-transformer.py:274` | `compute-term-entity-id()` | public |
| `application/core/publication-term-data-source.py:310` | `-compute-entity-id()` | private |

Обе реализации:
```python
normalized-term = term.lower().strip() if term else ""
composite = f"{document-chembl-id}:{term-type}:{normalized-term}"
return hashlib.sha256(composite.encode()).hexdigest()[:16]
```

**Риск бездействия:** Drift хеш-логики между двумя путями → нарушение дедупликации
и воспроизводимости primary key.

**Корректировка:**
1. Извлечь функцию `compute-publication-term-entity-id()` в общий модуль
   (предпочтительно `application/core/publication-term-utils.py` или в domain
   если это чистая бизнес-логика)
2. Заменить оба вызова на использование общей функции
3. Добавить unit-тест на стабильность хеша (idempotency)

**Затрагиваемые файлы:**
- `src/bioetl/application/pipelines/chembl/publication-term-transformer.py` → EDIT
- `src/bioetl/application/core/publication-term-data-source.py` → EDIT
- Новый модуль с общей функцией → CREATE

---

### FIX-3: Удалить подтверждённый dead code [MEDIUM]

**Подтверждённые dead-функции** (0 вызовов в src/ и tests/):

| # | Файл | Функция | Доказательство |
|---|------|---------|----------------|
| 1 | `composition/services/versioning.py:164` | `get-full-git-commit()` | Не экспортируется в `--all--`, 0 вызовов. `get-git-commit()` (short) используется |
| 2 | `composition/services/versioning.py:188` | `is-git-dirty()` | 0 вызовов |
| 3 | `infrastructure/adapters/http/rate-limiter.py:155` | `create-uniprot-bucket()` | Не экспортируется в `--init--.py`, factory использует ProviderRegistry |
| 4 | `infrastructure/adapters/http/rate-limiter.py:172` | `create-openalex-bucket()` | 0 вызовов |
| 5 | `infrastructure/adapters/http/rate-limiter.py:184` | `create-crossref-bucket()` | 0 вызовов |
| 6 | `application/composite/deduplication.py:219` | `value-to-string()` | Заменена на `-to-string-expr()` / `-build-concat-expr()` |

**Корректировка:**
1. Удалить все 6 функций
2. Запустить `pytest` для regression-проверки

**Затрагиваемые файлы:**
- `src/bioetl/composition/services/versioning.py` → EDIT (удалить 2 функции)
- `src/bioetl/infrastructure/adapters/http/rate-limiter.py` → EDIT (удалить 3 функции)
- `src/bioetl/application/composite/deduplication.py` → EDIT (удалить 1 функцию)

---

### FIX-4: Удалить orphan domain schemas [MEDIUM]

**Подтверждённые orphan-схемы** (не экспортируются в `--init--.py`, 0 production-импортов):

| # | Файл | Класс | Тест-импорты |
|---|------|-------|--------------|
| 1 | `domain/schemas/chembl/molecule-form.py` | `MoleculeFormSchema` | только тесты |
| 2 | `domain/schemas/chembl/target-relation.py` | `TargetRelationSchema` | только тесты |
| 3 | `domain/schemas/crossref/author.py` | `AuthorSchema` | только тесты |
| 4 | `domain/schemas/crossref/funder.py` | `FunderSchema` | только тесты |
| 5 | `domain/schemas/crossref/reference.py` | `ReferenceSchema` | только тесты |
| 6 | `domain/schemas/uniprot/isoform.py` | `IsoformSchema` | только тесты |

**Корректировка:**
1. Удалить 6 schema-файлов
2. Удалить или обновить соответствующие тесты
3. Убедиться, что `--init--.py` пакетов не экспортируют эти классы (проверено — не экспортируют)

**Затрагиваемые файлы:**
- 6 файлов schema → DELETE
- Соответствующие тест-файлы → DELETE/EDIT

---

### FIX-5: Очистить дублирующиеся импорты [LOW]

**Подтверждённые дубли** (runtime-импорт + избыточный TYPE-CHECKING-импорт):

| # | Файл | Символ | Runtime | TYPE-CHECKING | Действие |
|---|------|--------|---------|---------------|----------|
| 1 | `composition/factories/pipeline-factory.py` | `MetadataCoordinator` | строка 29 | строка 47 | Удалить из TYPE-CHECKING |
| 2 | `composition/factories/storage-adapter.py` | `datetime` | строка 16 | строка 29 | Удалить из TYPE-CHECKING |

**Отклонённый дубль (false positive):**
- `infrastructure/schemas/base-schemas.py` — `DomainFilterColumn` в TYPE-CHECKING (для type hints)
  и в `to-domain()` (для runtime instantiation). **Оба нужны** — разные scopes.

**Корректировка:**
1. Удалить `MetadataCoordinator` из TYPE-CHECKING-блока в `pipeline-factory.py:47`
2. Удалить `datetime` из TYPE-CHECKING-блока в `storage-adapter.py:29`

**Затрагиваемые файлы:**
- `src/bioetl/composition/factories/pipeline-factory.py` → EDIT
- `src/bioetl/composition/factories/storage-adapter.py` → EDIT

---

### FIX-6: Решить статус TEST-ONLY utility [LOW]

**Проблема:** `adapter-error-logging.py` содержит функцию `log-adapter-error()`,
которая используется только в тестах, но лежит в production-коде.

| Файл | Функция | Prod usage | Test usage |
|------|---------|------------|------------|
| `infrastructure/adapters/adapter-error-logging.py:18` | `log-adapter-error()` | 0 | 2+ файла |

**Варианты:**
- **A.** Перенести в `tests/helpers/` или `tests/conftest.py` (если это тестовая утилита)
- **B.** Интегрировать в production-адаптеры (если планировалось использовать)
- **C.** Удалить вместе с тестами (если не нужна)

**Рекомендация:** Вариант A — перенести в тестовый код.

**Затрагиваемые файлы:**
- `src/bioetl/infrastructure/adapters/adapter-error-logging.py` → DELETE
- `tests/helpers/adapter-error-logging.py` → CREATE (перенос)
- Тесты → EDIT (обновить imports)

---

## 3. Приоритизация и зависимости

```
Приоритет    Задача     Зависимости    Риск регрессии
─────────    ──────     ───────────    ──────────────
1 (HIGH)     FIX-1      нет            Низкий (dead code deletion)
2 (HIGH)     FIX-2      нет            Средний (hash logic change)
3 (MEDIUM)   FIX-3      нет            Низкий (dead code deletion)
4 (MEDIUM)   FIX-4      нет            Низкий (test-only schemas)
5 (LOW)      FIX-5      нет            Минимальный (import cleanup)
6 (LOW)      FIX-6      нет            Минимальный (test utility move)
```

Задачи **независимы** и могут выполняться параллельно. Порядок — по severity / risk.

---

## 4. Сводка по отклонённым vs подтверждённым

| ID | Находка аудита | Severity (заявлена) | Вердикт | Обоснование |
|----|----------------|---------------------|---------|-------------|
| FP-1 | infra→domain imports | CRITICAL | **FALSE POSITIVE** | ARCH-001/EXC-012/ADR-005 явно разрешают |
| FP-2 | GoldFiltersConfig.to-domain дубль | HIGH | **FALSE POSITIVE** | Разные класс-иерархии, не связаны наследованием |
| FIX-1 | Дублирующие pipeline-классы | HIGH | **CONFIRMED** | Dead modules с 0 prod-usage |
| FIX-2 | Entity ID hash duplication | HIGH | **CONFIRMED** | Byte-for-byte идентичная бизнес-логика |
| FIX-3 | Dead functions (6 шт.) | MEDIUM | **CONFIRMED** | 0 вызовов в src/ и tests/ |
| FIX-4 | Orphan schemas (6 шт.) | MEDIUM | **CONFIRMED** | Не экспортируются, 0 prod-imports |
| FIX-5 | Redundant imports (2 шт.) | LOW | **CONFIRMED** | TYPE-CHECKING дубли runtime-импортов |
| FIX-6 | TEST-ONLY utility | LOW | **CONFIRMED** | Prod-файл используется только в тестах |

---

## 5. Команды верификации после корректировки

```bash
# Полный тестовый прогон
pytest tests/ -x -q

# Архитектурные тесты
pytest tests/test-architecture.py -v

# Type check
mypy src/bioetl/ --strict

# Import lint
ruff check src/bioetl/ --select F401,F811

# Coverage (threshold 85%)
pytest --cov=src/bioetl --cov-fail-under=85
```

---

*Документ подготовлен на основе перекрёстной валидации 3 аудиторских отчётов
с фактическим состоянием кодовой базы, правилами проекта (RULES.md, ai-selfreview-rules.md),
архитектурными решениями (ADR-005) и автоматическими тестами (test-architecture.py).*
