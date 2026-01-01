# Задача: Дополнение пропущенных docstrings в проекте BioETL

## Контекст
Проект BioETL следует RULES.md v5.0. Согласно §10.3:
- Публичные классы/функции **MUST** иметь docstring
- Язык docstrings — английский
- Стиль — Google-style docstrings

## Область применения
Директория: `src/bioetl/`
Слои (в порядке приоритета):
1. `domain/` — Protocols, Models, Schemas, Services
2. `application/` — Pipelines, Observers
3. `infrastructure/` — Adapters, Storage, Locking
4. `interfaces/` — CLI

## Правила генерации docstrings

### 1. Формат (Google-style)
```python
def fetch_batch(self, query: Query, limit: int = 100) -> Iterator[RawRecord]:
    """Fetch records from upstream API in batches.
    
    Args:
        query: Query parameters for filtering records.
        limit: Maximum records per batch. Defaults to 100.
    
    Returns:
        Iterator yielding raw records from the API.
    
    Raises:
        RateLimitError: If API rate limit is exceeded.
        CircuitOpenError: If circuit breaker is open (§3.1.4).
    
    Note:
        Implements exponential backoff per §3.1.3.
    """
```

### 2. Обязательные элементы

| Элемент | Когда включать |
|---------|----------------|
| Summary | Всегда (первая строка) |
| Args | Если есть параметры (кроме self/cls) |
| Returns | Если возвращает не None |
| Raises | Если явно поднимает исключения |
| Note | Ссылки на RULES.md (§X.Y) |
| Example | Для сложных API |

### 3. Ссылки на RULES.md
Включать ссылки на соответствующие секции:
- `§2.1` — Medallion Architecture
- `§2.6` — Quarantine
- `§2.8.1` — Content Hash
- `§3.1.4` — Circuit Breaker
- `§3.3` — Locking
- `§5.4` — Sensitive Data

### 4. Шаблоны по типу компонента

**Protocol (domain/ports.py):**
```python
class DataSourcePort(Protocol):
    """Port for data source interactions.
    
    Defines contract for extracting data from external providers.
    Implementations must handle rate limiting and circuit breaker (§3.1.4).
    """
```

**Service (domain/services/):**
```python
class HashService:
    """Compute deterministic content hashes for records.
    
    Implements Robust Content Hash algorithm per §2.8.1:
    - NaN/Inf → null
    - Floats → round(val, 10)
    - Dates → ISO format YYYY-MM-DD
    - Excludes meta-fields: _ingestion_ts, _run_id, _run_type, _dq_*
    """
```

**Pipeline (application/pipelines/):**
```python
class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL activity data extraction and loading.

    Follows Medallion Architecture (§2.1):
        Bronze: JSONL + zstd (append-only)
        Silver: Delta Lake (merge/upsert)
        Gold: Delta Lake (strict validation)

    Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
    """
```

**Adapter (infrastructure/adapters/):**
```python
class ChemblClient:
    """HTTP client for ChEMBL REST API.
    
    Features:
        - Rate limiting via TokenBucket (§5.1)
        - Circuit breaker protection (§3.1.4)
        - Exponential backoff retry (§3.1.3)
    
    Health check endpoint: GET /chembl/api/data/status.json
    """
```

## Процедура выполнения

### Шаг 1: Сканирование
```bash
# Найти файлы без docstrings в публичных элементах
grep -rL '"""' src/bioetl/**/*.py | head -20
```

### Шаг 2: Приоритизация
1. Protocols в `domain/ports.py`
2. Публичные классы в `domain/`
3. Pipeline классы в `application/`
4. Adapter классы в `infrastructure/`

### Шаг 3: Генерация
Для каждого файла:
1. Прочитать код и понять назначение
2. Определить связь с секциями RULES.md
3. Сгенерировать docstring в Google-style
4. Добавить ссылки на §X.Y где релевантно

### Шаг 4: Валидация
```bash
# Проверка наличия docstrings
pydocstyle src/bioetl/ --convention=google

# Проверка типов
mypy src/bioetl/ --strict
```

## Ограничения

- **НЕ** менять логику кода, только добавлять docstrings
- **НЕ** добавлять docstrings к приватным методам (_method)
- **НЕ** дублировать информацию из type hints в описании Args
- Максимум 3-5 файлов за один проход (атомарность)

## Формат вывода

Для каждого файла предоставить unified diff:
```diff
--- a/src/bioetl/domain/services/hash_service.py
+++ b/src/bioetl/domain/services/hash_service.py
@@ -10,6 +10,15 @@
 class HashService:
+    """Compute deterministic content hashes for records.
+    
+    Implements Robust Content Hash algorithm per §2.8.1.
+    """
+
     PRECISION = 10
```

## Пример запроса

> Добавь docstrings в файл `src/bioetl/domain/services/hash_service.py`.
> Следуй Google-style, включи ссылки на §2.8.1.