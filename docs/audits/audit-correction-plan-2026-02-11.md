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
| **tests/test_architecture.py** | `test_infrastructure_boundaries` проверяет только infra→app (запрещено), infra→domain **не проверяется как нарушение** |

Примечание к ARCH-001 прямо гласит:
> *«Infrastructure может импортировать **любые** domain-модули (ports, types, exceptions,
> entities, config, models, value_objects, serialization и т.д.)»*

Все 146 импортов попадают в разрешённые категории EXC-012. Архитектурные тесты
подтверждают: запрет действует только на infra→application.

**Действие:** Закрыть как false positive. Инструкции аудита скорректировать —
ссылаться на ARCH-001/EXC-012/ADR-005 как на авторитетные правила границ.

---

#### FP-2: GoldFiltersConfig.to_domain дублирование (заявлено как HIGH)

**Вердикт: FALSE POSITIVE — намеренный архитектурный паттерн.**

| Файл | Класс | Назначение |
|------|-------|------------|
| `base_schemas.py:551` | `BaseGoldFiltersConfig.to_domain()` | Базовый класс для standalone filter configs |
| `pipeline_config.py:795` | `GoldFiltersConfig.to_domain()` | Независимая реализация для YAML pipeline config |

Два класса **не связаны наследованием** — они обслуживают разные ветки конфигурации
(inline pipeline vs external filter files). `filter_config.py` использует type alias'ы
на base-классы, а `pipeline_config.py` имеет собственную иерархию. Одинаковая логика
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
в `__init__.py` (используется в production) и в отдельном модуле (не используется).

| Пакет | `__init__.py` (production) | Модуль-дубль (dead) |
|-------|---------------------------|---------------------|
| pubchem | `__init__.py:17` — PubChemCompoundPipeline | `compound.py:11` |
| pubmed | `__init__.py:17` — PubMedPublicationPipeline | `publication.py:12` |
| uniprot | `__init__.py:21` — UniProtProteinPipeline | `protein.py:11` |

**Доказательство:** `compound.py`, `publication.py`, `protein.py` имеют 0 production-импортов.
Все factory/composition imports идут через `__init__.py`.

**Риск бездействия:** Расхождение реализаций при будущих изменениях, ложная сложность
при инвентаризации.

**Корректировка:**
1. Удалить `compound.py`, `publication.py`, `protein.py`
2. Проверить, что тесты, импортирующие напрямую из этих модулей, переключены на import
   из `__init__.py` (package level)
3. Запустить `pytest tests/` для regression-проверки

**Затрагиваемые файлы:**
- `src/bioetl/application/pipelines/pubchem/compound.py` → DELETE
- `src/bioetl/application/pipelines/pubmed/publication.py` → DELETE
- `src/bioetl/application/pipelines/uniprot/protein.py` → DELETE
- Тесты: обновить imports если требуется

---

### FIX-2: Централизовать хеширование publication-term entity ID [HIGH]

**Проблема:** Идентичная логика вычисления entity_id для publication_term
дублируется byte-for-byte в двух местах:

| Файл | Метод | Видимость |
|------|-------|-----------|
| `application/pipelines/chembl/publication_term_transformer.py:274` | `compute_term_entity_id()` | public |
| `application/core/publication_term_data_source.py:310` | `_compute_entity_id()` | private |

Обе реализации:
```python
normalized_term = term.lower().strip() if term else ""
composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
return hashlib.sha256(composite.encode()).hexdigest()[:16]
```

**Риск бездействия:** Drift хеш-логики между двумя путями → нарушение дедупликации
и воспроизводимости primary key.

**Корректировка:**
1. Извлечь функцию `compute_publication_term_entity_id()` в общий модуль
   (предпочтительно `application/core/publication_term_utils.py` или в domain
   если это чистая бизнес-логика)
2. Заменить оба вызова на использование общей функции
3. Добавить unit-тест на стабильность хеша (idempotency)

**Затрагиваемые файлы:**
- `src/bioetl/application/pipelines/chembl/publication_term_transformer.py` → EDIT
- `src/bioetl/application/core/publication_term_data_source.py` → EDIT
- Новый модуль с общей функцией → CREATE

---

### FIX-3: Удалить подтверждённый dead code [MEDIUM]

**Подтверждённые dead-функции** (0 вызовов в src/ и tests/):

| # | Файл | Функция | Доказательство |
|---|------|---------|----------------|
| 1 | `composition/services/versioning.py:164` | `get_full_git_commit()` | Не экспортируется в `__all__`, 0 вызовов. `get_git_commit()` (short) используется |
| 2 | `composition/services/versioning.py:188` | `is_git_dirty()` | 0 вызовов |
| 3 | `infrastructure/adapters/http/rate_limiter.py:155` | `create_uniprot_bucket()` | Не экспортируется в `__init__.py`, factory использует ProviderRegistry |
| 4 | `infrastructure/adapters/http/rate_limiter.py:172` | `create_openalex_bucket()` | 0 вызовов |
| 5 | `infrastructure/adapters/http/rate_limiter.py:184` | `create_crossref_bucket()` | 0 вызовов |
| 6 | `application/composite/deduplication.py:219` | `value_to_string()` | Заменена на `_to_string_expr()` / `_build_concat_expr()` |

**Корректировка:**
1. Удалить все 6 функций
2. Запустить `pytest` для regression-проверки

**Затрагиваемые файлы:**
- `src/bioetl/composition/services/versioning.py` → EDIT (удалить 2 функции)
- `src/bioetl/infrastructure/adapters/http/rate_limiter.py` → EDIT (удалить 3 функции)
- `src/bioetl/application/composite/deduplication.py` → EDIT (удалить 1 функцию)

---

### FIX-4: Удалить orphan domain schemas [MEDIUM]

**Подтверждённые orphan-схемы** (не экспортируются в `__init__.py`, 0 production-импортов):

| # | Файл | Класс | Тест-импорты |
|---|------|-------|--------------|
| 1 | `domain/schemas/chembl/molecule_form.py` | `MoleculeFormSchema` | только тесты |
| 2 | `domain/schemas/chembl/target_relation.py` | `TargetRelationSchema` | только тесты |
| 3 | `domain/schemas/crossref/author.py` | `AuthorSchema` | только тесты |
| 4 | `domain/schemas/crossref/funder.py` | `FunderSchema` | только тесты |
| 5 | `domain/schemas/crossref/reference.py` | `ReferenceSchema` | только тесты |
| 6 | `domain/schemas/uniprot/isoform.py` | `IsoformSchema` | только тесты |

**Корректировка:**
1. Удалить 6 schema-файлов
2. Удалить или обновить соответствующие тесты
3. Убедиться, что `__init__.py` пакетов не экспортируют эти классы (проверено — не экспортируют)

**Затрагиваемые файлы:**
- 6 файлов schema → DELETE
- Соответствующие тест-файлы → DELETE/EDIT

---

### FIX-5: Очистить дублирующиеся импорты [LOW]

**Подтверждённые дубли** (runtime-импорт + избыточный TYPE_CHECKING-импорт):

| # | Файл | Символ | Runtime | TYPE_CHECKING | Действие |
|---|------|--------|---------|---------------|----------|
| 1 | `composition/factories/pipeline_factory.py` | `MetadataCoordinator` | строка 29 | строка 47 | Удалить из TYPE_CHECKING |
| 2 | `composition/factories/storage_adapter.py` | `datetime` | строка 16 | строка 29 | Удалить из TYPE_CHECKING |

**Отклонённый дубль (false positive):**
- `infrastructure/schemas/base_schemas.py` — `DomainFilterColumn` в TYPE_CHECKING (для type hints)
  и в `to_domain()` (для runtime instantiation). **Оба нужны** — разные scopes.

**Корректировка:**
1. Удалить `MetadataCoordinator` из TYPE_CHECKING-блока в `pipeline_factory.py:47`
2. Удалить `datetime` из TYPE_CHECKING-блока в `storage_adapter.py:29`

**Затрагиваемые файлы:**
- `src/bioetl/composition/factories/pipeline_factory.py` → EDIT
- `src/bioetl/composition/factories/storage_adapter.py` → EDIT

---

### FIX-6: Решить статус TEST_ONLY utility [LOW]

**Проблема:** `adapter_error_logging.py` содержит функцию `log_adapter_error()`,
которая используется только в тестах, но лежит в production-коде.

| Файл | Функция | Prod usage | Test usage |
|------|---------|------------|------------|
| `infrastructure/adapters/adapter_error_logging.py:18` | `log_adapter_error()` | 0 | 2+ файла |

**Варианты:**
- **A.** Перенести в `tests/helpers/` или `tests/conftest.py` (если это тестовая утилита)
- **B.** Интегрировать в production-адаптеры (если планировалось использовать)
- **C.** Удалить вместе с тестами (если не нужна)

**Рекомендация:** Вариант A — перенести в тестовый код.

**Затрагиваемые файлы:**
- `src/bioetl/infrastructure/adapters/adapter_error_logging.py` → DELETE
- `tests/helpers/adapter_error_logging.py` → CREATE (перенос)
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
| FP-2 | GoldFiltersConfig.to_domain дубль | HIGH | **FALSE POSITIVE** | Разные класс-иерархии, не связаны наследованием |
| FIX-1 | Дублирующие pipeline-классы | HIGH | **CONFIRMED** | Dead modules с 0 prod-usage |
| FIX-2 | Entity ID hash duplication | HIGH | **CONFIRMED** | Byte-for-byte идентичная бизнес-логика |
| FIX-3 | Dead functions (6 шт.) | MEDIUM | **CONFIRMED** | 0 вызовов в src/ и tests/ |
| FIX-4 | Orphan schemas (6 шт.) | MEDIUM | **CONFIRMED** | Не экспортируются, 0 prod-imports |
| FIX-5 | Redundant imports (2 шт.) | LOW | **CONFIRMED** | TYPE_CHECKING дубли runtime-импортов |
| FIX-6 | TEST_ONLY utility | LOW | **CONFIRMED** | Prod-файл используется только в тестах |

---

## 5. Команды верификации после корректировки

```bash
# Полный тестовый прогон
pytest tests/ -x -q

# Архитектурные тесты
pytest tests/test_architecture.py -v

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
архитектурными решениями (ADR-005) и автоматическими тестами (test_architecture.py).*
