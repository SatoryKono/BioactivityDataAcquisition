# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-05
**Версия**: 1.0
**Автор**: Claude Code Agent
**Методология**: Двойная верификация согласно RULES.md §7 (REQ-ARCH-040)

---

## Executive Summary

| Метрика | Значение |
|---------|----------|
| **Обнаружено дублирований** | 1 верифицированное |
| **Потенциальное сокращение** | ~100 LOC (50 LOC × 2 файла) |
| **Приоритет P1** | 1 задача |
| **Валидные паттерны (НЕ дублирование)** | 4 категории |

### Ключевые выводы

1. **Кодовая база BioETL уже хорошо абстрагирована**:
   - `BaseChemblTransformer` с декларативным DSL (`FieldGroup`, `FieldSpec`)
   - `BaseTransformer` для всех трансформеров
   - `BaseHttpAdapter` / `BaseSyncAdapter` для адаптеров
   - `BaseFieldExtractor` для PubMed extractors

2. **Найдено одно верифицированное дублирование** в storage layer, которое легко устранить наследованием от существующего `BaseDeltaWriter`.

---

## 1. Верифицированные дублирования

### 1.1 SilverWriter / GoldWriter — `get_table_path()` и `clear()`

#### Верификация (ОБЯЗАТЕЛЬНАЯ)
| Поле | Значение |
|------|----------|
| **Файлы** | `silver_writer.py`, `gold_writer.py` |
| **Строки** | `silver_writer.py:639-688`, `gold_writer.py:574-623` |
| **LOC дублирования** | ~50 LOC × 2 файла = **100 LOC** |
| **Паттерн** | Идентичная реализация методов `get_table_path()` и `clear()` |
| **Дата проверки** | 2026-01-05 |
| **Статус** | Нет в `refactoring-plan.md:ЛОЖНЫЕ_УТВЕРЖДЕНИЯ` ✅ |

#### Текущее состояние

**SilverWriter** (`silver_writer.py:639-688`):
```python
def get_table_path(self, table_name: str) -> Path:
    from pathlib import Path
    return Path(self.base_path) / table_name.replace(".", "/")

def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
    import shutil
    from pathlib import Path
    base = Path(self.base_path)
    if not base.exists():
        return 0
    cleared = 0
    if table_name:
        table_path = self.get_table_path(table_name)
        if table_path.exists():
            if not dry_run:
                shutil.rmtree(table_path)
            cleared = 1
    else:
        for item in base.iterdir():
            if item.is_dir() and (item / "_delta_log").exists():
                if not dry_run:
                    shutil.rmtree(item)
                cleared += 1
    return cleared
```

**GoldWriter** (`gold_writer.py:574-623`):
```python
# ИДЕНТИЧНАЯ РЕАЛИЗАЦИЯ с минимальным отличием в docstring
```

**BaseDeltaWriter** (`base_delta_writer.py:106-134`) — **уже содержит эти методы**:
```python
def get_table_path(self, table_name: str) -> Path:
    from pathlib import Path
    return Path(self.base_path) / table_name.replace(".", "/")

def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
    # Идентичная реализация
```

#### Причина дублирования

`SilverWriter` и `GoldWriter` **не наследуют** от `BaseDeltaWriter`:

```python
# Текущее состояние (silver_writer.py:68)
class SilverWriter:  # Нет наследования!

# Текущее состояние (gold_writer.py:50)
class GoldWriter:    # Нет наследования!
```

#### Предлагаемое решение

```python
# silver_writer.py
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

class SilverWriter(BaseDeltaWriter):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        # ... остальные параметры
    ) -> None:
        super().__init__(base_path, logger)
        # SilverWriter-специфичная инициализация
        self._tracing = tracing or NoOpTracing()
        # ...

    # Удалить методы get_table_path() и clear() — они унаследованы
```

```python
# gold_writer.py
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter

class GoldWriter(BaseDeltaWriter):
    """Writer for Gold layer (validated business data)."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        # ... параметры
    ) -> None:
        super().__init__(base_path, logger)
        # GoldWriter-специфичная инициализация
        # ...

    # Удалить методы get_table_path() и clear() — они унаследованы
```

#### План миграции

| Шаг | Действие | Файлы |
|-----|----------|-------|
| 1 | Добавить наследование от `BaseDeltaWriter` | `silver_writer.py`, `gold_writer.py` |
| 2 | Удалить дублированные методы | `silver_writer.py:639-688`, `gold_writer.py:574-623` |
| 3 | Обновить `__init__` для вызова `super().__init__()` | Оба файла |
| 4 | Запустить тесты | `make test` |
| 5 | Проверить архитектурные тесты | `make arch-test` |

#### Критерии завершения

- [ ] `SilverWriter` наследует от `BaseDeltaWriter`
- [ ] `GoldWriter` наследует от `BaseDeltaWriter`
- [ ] Методы `get_table_path()` и `clear()` удалены из дочерних классов
- [ ] Все тесты проходят (`make test`)
- [ ] Архитектурные тесты проходят (`make arch-test`)
- [ ] Mypy strict проходит (`mypy src/bioetl --strict`)

#### Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Конфликт `__init__` параметров | LOW | MEDIUM | Внимательно сравнить параметры конструкторов |
| Изменение поведения | LOW | HIGH | Комплексное тестирование |

---

## 2. Валидные паттерны (НЕ являются дублированием)

### 2.1 ChEMBL Transformers с DSL

| Файл | LOC | Паттерн |
|------|-----|---------|
| `base_chembl_transformer.py` | 166 | Template Method + ABC |
| `field_specs.py` | 270 | Declarative DSL |

**Почему НЕ дублирование:**
- Каждый transformer реализует уникальный `_extract_business_data()`
- DSL (`FieldGroup`, `FieldSpec`) централизует маппинг полей
- `map_field_groups()` переиспользуется во всех ChEMBL transformers

```python
# Пример использования DSL (activity_transformer.py)
_ACTIVITY_GROUPS = (
    _IDENTIFIERS,        # FieldGroup
    _MOLECULE_TARGET,    # FieldGroup
    _RAW_VALUES,         # FieldGroup
)

def _extract_business_data(self, record, primary_id):
    return {
        "activity_id": str(primary_id),
        **map_field_groups(record, _ACTIVITY_GROUPS),  # DSL в действии
    }
```

### 2.2 Non-ChEMBL Transformers

| Файл | LOC | Base Class |
|------|-----|------------|
| `uniprot/transformer.py` | 177 | `BaseTransformer` |
| `pubchem/transformer.py` | 116 | `BaseTransformer` |
| `crossref/transformer.py` | 263 | `BaseTransformer` |
| `pubmed/transformer.py` | 178 | `BaseTransformer` |

**Почему НЕ дублирование:**
- Общий алгоритм в `BaseTransformer._transform_impl()` wrapper
- Бизнес-логика извлечения данных уникальна для каждого провайдера
- Каждый провайдер имеет разный формат входных данных (JSON vs XML vs FASTA)

**Потенциальное улучшение (LOW PRIORITY):**
- Унифицировать структуру `_transform_impl` через Template Method (как в ChEMBL)
- Добавить поддержку `FieldGroup` DSL для простых провайдеров
- **Impact**: LOW — текущая реализация читаема и maintainable

### 2.3 HTTP Adapters

| Файл | LOC | Base Class |
|------|-----|------------|
| `base.py` | 272 | `BaseHttpAdapter` |
| `sync_base.py` | 280 | `BaseSyncAdapter` |
| `chembl/client.py` | 659 | `BaseHttpAdapter` |
| `crossref/client.py` | 393 | `BaseHttpAdapter` |
| `uniprot/client.py` | 348 | `BaseHttpAdapter` |
| `pubchem/client.py` | 305 | `BaseSyncAdapter` |

**Почему НЕ дублирование:**
- `fetch()`, `fetch_filtered()` — **полиморфизм** (разные реализации одного интерфейса)
- `health_check()` — Template Method в `BaseHttpAdapter`
- Каждый провайдер имеет уникальный API (REST vs SOAP vs GraphQL-like)

### 2.4 PubMed Extractors

| Файл | LOC | Base Class |
|------|-----|------------|
| `extractors/base.py` | 65 | `BaseFieldExtractor` (ABC) |
| `extractors/date.py` | 203 | `BaseFieldExtractor` |
| `extractors/classification.py` | 151 | `BaseFieldExtractor` |
| `extractors/identifier.py` | 130 | `BaseFieldExtractor` |
| `extractors/author.py` | 112 | `BaseFieldExtractor` |
| `extractors/abstract.py` | 75 | `BaseFieldExtractor` |

**Почему НЕ дублирование:**
- Strategy Pattern для XML-извлечения
- Каждый extractor обрабатывает специфичную часть PubMed XML
- Базовый класс предоставляет общие утилиты (`get_text()`)

---

## 3. Матрица приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет |
|---|-----------|--------|------------|-----|-----------|
| 1 | SilverWriter/GoldWriter inheritance | MEDIUM | LOW | 100 | **P1** |

---

## 4. План рефакторинга

### Фаза 1: Storage Layer Inheritance (P1)

**Объём**: ~100 LOC удаление, ~10 LOC добавление
**Файлы**: `silver_writer.py`, `gold_writer.py`

#### Задачи

1. **Добавить наследование от BaseDeltaWriter**
   - `SilverWriter(BaseDeltaWriter)`
   - `GoldWriter(BaseDeltaWriter)`

2. **Обновить `__init__` методы**
   - Вызвать `super().__init__(base_path, logger)`
   - Убрать дублирование `self.base_path = ...`

3. **Удалить дублированные методы**
   - `get_table_path()` — 13 LOC × 2
   - `clear()` — 37 LOC × 2

4. **Валидация**
   ```bash
   make lint && make test && make arch-test
   ```

---

## 5. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Конфликт инициализации | LOW | MEDIUM | Ревью параметров `__init__` |
| Регрессия поведения | LOW | HIGH | Полное тестовое покрытие |
| Нарушение архитектурных границ | VERY LOW | HIGH | `make arch-test` |

---

## 6. Отвергнутые предложения

### 6.1 Создание BaseEntityTransformer для non-ChEMBL

**Предложение**: Создать общий базовый класс для UniProt, PubChem, CrossRef, PubMed transformers.

**Причина отклонения**:
- Текущая архитектура достаточно чистая
- Бизнес-логика извлечения данных слишком различается между провайдерами
- `BaseTransformer` уже предоставляет необходимые хуки
- Impact/Complexity ratio низкий

### 6.2 Внедрение FieldGroup DSL в non-ChEMBL transformers

**Предложение**: Использовать `FieldGroup` DSL для UniProt/PubChem/CrossRef.

**Причина отклонения**:
- DSL оптимизирован для flat JSON структур (ChEMBL)
- UniProt/PubMed имеют вложенные/XML структуры
- CrossRef имеет сложную логику нормализации
- Текущая реализация читаема и maintainable

---

## 7. Приложение A: Команды верификации

```bash
# Верификация дублирования в storage
diff <(sed -n '639,688p' src/bioetl/infrastructure/storage/silver_writer.py) \
     <(sed -n '574,623p' src/bioetl/infrastructure/storage/gold_writer.py)

# Проверка inheritance
grep -n "class.*Writer" src/bioetl/infrastructure/storage/*.py

# Размеры файлов
wc -l src/bioetl/infrastructure/storage/*.py | sort -rn

# Поиск повторяющихся методов
grep -h "def _" src/bioetl/application/pipelines/*/*.py | \
  sed 's/^[[:space:]]*//' | sort | uniq -c | sort -rn | head -20

# Проверка против ложных утверждений
grep -E "SilverWriter|GoldWriter" docs/refactoring-plan.md
```

---

## 8. Приложение B: Статистика кодовой базы

| Область | Файлов | LOC | Комментарий |
|---------|--------|-----|-------------|
| `application/pipelines/` | 40 | ~4,500 | Хорошо абстрагировано |
| `infrastructure/adapters/` | 41 | ~8,950 | Полиморфизм, базовые классы |
| `infrastructure/storage/` | 7 | ~2,685 | **Найдено дублирование** |
| **Итого** | 88 | ~16,135 | |

---

**END OF REPORT**
