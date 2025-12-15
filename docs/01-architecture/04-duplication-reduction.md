# Duplication Reduction
*Aligned with RULES.md v5.0*

## Философия (§1)

> "Прагматичная инженерия". Избегаем избыточной сложности (Over-engineering).

**Принцип**: Применять паттерны только там, где они дают реальную пользу. ABC/Impl создаётся только при наличии >1 реализации.

---

## Паттерн Protocol vs ABC (§1.1.1)

### Protocol (Предпочтительно)

Используется для определения контрактов в `domain/ports.py`:

```python
from typing import Protocol

class DataSourcePort(Protocol):
    """Контракт для источника данных."""
    async def fetch(self, query: Query) -> Iterator[RawRecord]: ...
    async def health_check(self) -> bool: ...
```

**Преимущества**:
- Структурная типизация (duck typing)
- Не требует наследования
- Проверка `mypy --strict` на этапе сборки

### ABC (Только при необходимости)

Используется когда нужна общая реализация или состояние:

```python
from abc import ABC, abstractmethod

class TransformerBase(ABC):
    """Базовый трансформер с общей логикой."""
    
    def __init__(self, hash_service: HashService):
        self._hash_service = hash_service
    
    def transform(self, records: list[dict]) -> list[dict]:
        normalized = self._normalize(records)
        return self._add_hashes(normalized)
    
    @abstractmethod
    def _normalize(self, records: list[dict]) -> list[dict]:
        """Специфичная для сущности нормализация."""
        ...
    
    def _add_hashes(self, records: list[dict]) -> list[dict]:
        """Общая логика хэширования."""
        for record in records:
            record["_content_hash"] = self._hash_service.compute(record)
        return records
```

### Критерий Выбора

| Сценарий | Паттерн |
|----------|---------|
| Контракт без состояния | `Protocol` |
| Контракт + общая логика | `ABC` |
| Единственная реализация | Класс напрямую (без ABC) |

---

## Иерархия Пайплайнов

### Уровни Наследования

```
PipelineBase                          # Общий каркас стадий
    │
    ├── ChemblPipelineBase            # Специфика ChEMBL
    │       │
    │       └── ChemblCommonPipeline  # Общая логика ChEMBL-сущностей
    │               │
    │               ├── ChemblActivityPipeline
    │               ├── ChemblAssayPipeline
    │               ├── ChemblTargetPipeline
    │               ├── ChemblMoleculePipeline
    │               └── ChemblDocumentPipeline
    │
    └── PubchemPipelineBase           # Специфика PubChem
            │
            └── PubchemCompoundPipeline
```

### PipelineBase

Минимальный каркас без привязки к провайдеру:

```python
class PipelineBase:
    """§1.1: Application Layer — оркестрация."""
    
    async def run(self) -> RunResult:
        try:
            await self.prepare_run()
            await self.extract()
            await self.transform()
            await self.validate()
            await self.load()
            return await self.finalize_run()
        except Exception as e:
            await self.on_error(e)
            raise
    
    @abstractmethod
    async def extract(self) -> None: ...
    
    @abstractmethod
    async def transform(self) -> None: ...
    
    # validate и load имеют default implementation
```

### ChemblCommonPipeline

Общая логика для всех ChEMBL-сущностей:

```python
class ChemblCommonPipeline(ChemblPipelineBase):
    """Шаблон для ChEMBL-пайплайнов."""
    
    def __init__(
        self,
        client: ChemblClient,
        transformer: TransformerBase,
        schema: pa.DataFrameSchema,
        writer: DeltaLakeWriter,
        lock: LockPort,
    ):
        self._client = client
        self._transformer = transformer
        self._schema = schema
        self._writer = writer
        self._lock = lock
    
    async def extract(self) -> None:
        # Общая логика извлечения с Circuit Breaker
        ...
    
    async def transform(self) -> None:
        # Делегирование специфичному трансформеру
        self._data = self._transformer.transform(self._raw_data)
```

### Конкретные Пайплайны

Переопределяют только специфичное:

```python
class ChemblActivityPipeline(ChemblCommonPipeline):
    """Пайплайн для Activity."""
    
    @property
    def entity(self) -> str:
        return "activity"
    
    @property
    def schema(self) -> pa.DataFrameSchema:
        return ActivityTableSchema
    
    def create_transformer(self) -> TransformerBase:
        return ActivityTransformer(self._hash_service)
```

---

## Общие Сервисы

### HashService (§2.8.1)

Единый сервис для вычисления Content Hash:

```python
class HashService:
    """Robust Content Hash — §2.8.1."""
    
    PRECISION = 10
    EXCLUDED_PREFIXES = ("_",)
    
    def compute(self, provider: str, data: dict) -> str:
        hashable = self._filter_hashable(data)
        normalized = self._normalize(hashable)
        canonical = self._canonical_json(normalized)
        return hashlib.sha256(f"{provider}{canonical}".encode()).hexdigest()
    
    def _normalize(self, data: dict) -> dict:
        """NaN→null, floats→round(10), dates→ISO."""
        ...
```

**Использование**: Внедряется через DI во все трансформеры.

### ValidationService (§2.6)

Единый сервис для Pandera-валидации:

```python
class ValidationService:
    """Централизованная валидация с маршрутизацией в Quarantine."""
    
    def __init__(
        self,
        schema_registry: SchemaRegistry,
        quarantine: QuarantinePort,
        metrics: MetricsPort,
    ):
        self._registry = schema_registry
        self._quarantine = quarantine
        self._metrics = metrics
    
    async def validate(
        self,
        entity: str,
        df: pl.DataFrame,
        batch_context: BatchContext,
    ) -> ValidationResult:
        schema = self._registry.get(entity)
        
        try:
            validated = schema.validate(df, lazy=True)
            errors = []
        except pa.errors.SchemaErrors as e:
            errors = e.failure_cases
        
        # Route to quarantine
        await self._route_failures(errors, batch_context)
        
        # Export metrics
        self._metrics.record_validation(entity, len(df), len(errors))
        
        return ValidationResult(validated, errors)
```

### NormalizationService (§2.8.1)

Стандартизация типов:

```python
class NormalizationService:
    """Нормализация значений для детерминизма."""
    
    def normalize_record(self, record: dict) -> dict:
        return {
            k: self._normalize_value(v)
            for k, v in record.items()
        }
    
    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return round(value, 10)
        
        if isinstance(value, datetime):
            return value.date().isoformat()
        
        if isinstance(value, str):
            return value.strip()
        
        return value
```

### SaltManager (§5.4.1)

Ротация соли для PII hashing:

```python
class SaltManager:
    """Dual-Salt rotation — §5.4.1."""
    
    def __init__(self, secrets_client: SecretsPort):
        self._secrets = secrets_client
    
    async def get_current_salt(self) -> str:
        return await self._secrets.get("BIOETL_SALT_CURRENT")
    
    async def get_next_salt(self) -> str | None:
        """Returns SALT_NEXT during transition period."""
        return await self._secrets.get("BIOETL_SALT_NEXT")
    
    async def hash_pii(self, value: str) -> str:
        """§5.4: PII fields MUST be salted."""
        salt = await self.get_current_salt()
        return hashlib.sha256(
            f"{value.lower()}{salt}".encode()
        ).hexdigest()
```

---

## Фабрики и Инверсия Зависимостей

### Client Factory

```python
class ClientFactory:
    """Создание клиентов с общей конфигурацией."""
    
    def __init__(
        self,
        rate_limiter: RateLimiterPort,
        circuit_breaker: CircuitBreakerPort,
        logger: LoggingPort,
    ):
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._logger = logger
    
    def create_chembl_client(self, config: ChemblConfig) -> ChemblClient:
        return ChemblClient(
            base_url=config.base_url,
            rate_limiter=self._rate_limiter,
            circuit_breaker=self._circuit_breaker,
            logger=self._logger,
        )
    
    def create_pubchem_client(self, config: PubchemConfig) -> PubchemClient:
        # Thread pool для sync library
        return PubchemClient(
            thread_pool=self._thread_pool,
            rate_limiter=self._rate_limiter,
            ...
        )
```

### Pipeline Container

DI-контейнер для сборки пайплайна:

```python
class PipelineContainer:
    """Dependency Injection container."""
    
    def __init__(self, config: PipelineConfig):
        self._config = config
        self._instances: dict[type, Any] = {}
    
    def get(self, port_type: type[T]) -> T:
        if port_type not in self._instances:
            self._instances[port_type] = self._create(port_type)
        return self._instances[port_type]
    
    def _create(self, port_type: type) -> Any:
        if port_type == LockPort:
            return RedisDistributedLock(
                redis_client=self.get(Redis),
                resource=f"{self._config.provider}_{self._config.entity}",
            )
        ...
```

---

## Повторное Использование между Пайплайнами

### Общие Transformer Mixins

```python
class NormalizerMixin:
    """Общая нормализация для всех трансформеров."""
    
    def normalize_types(self, record: dict) -> dict:
        return {
            k: self._normalize_value(v)
            for k, v in record.items()
        }

class HashMixin:
    """Добавление хэшей."""
    
    def add_hashes(self, record: dict, hash_service: HashService) -> dict:
        record["_content_hash"] = hash_service.compute(record)
        return record
```

### Descriptor Factory

Генерация параметров извлечения:

```python
class DescriptorFactory:
    """Генерация параметров для разных сущностей."""
    
    ENTITY_CONFIGS = {
        "activity": {
            "endpoint": "/activities",
            "batch_size": 1000,
            "fields": ["activity_id", "assay_id", ...],
        },
        "assay": {
            "endpoint": "/assays",
            "batch_size": 500,
            ...
        },
    }
    
    def create(self, entity: str) -> ExtractionDescriptor:
        config = self.ENTITY_CONFIGS[entity]
        return ExtractionDescriptor(**config)
```

---

## Матрица Переиспользования

| Компонент | Activity | Assay | Target | Molecule | Document |
|-----------|:--------:|:-----:|:------:|:--------:|:--------:|
| `HashService` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ValidationService` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `NormalizationService` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ChemblClient` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `DeltaLakeWriter` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `QuarantineWriter` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `RedisDistributedLock` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `CircuitBreaker` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ChemblCommonPipeline` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `NormalizerMixin` | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Anti-Patterns (Избегать)

### ❌ ABC без вариантов

```python
# Плохо: ABC для единственной реализации
class ActivityTransformerABC(ABC):
    @abstractmethod
    def transform(self, data): ...

class ActivityTransformerImpl(ActivityTransformerABC):
    def transform(self, data): ...
```

### ✓ Прямой класс

```python
# Хорошо: класс напрямую
class ActivityTransformer:
    def transform(self, data): ...
```

### ❌ God Object

```python
# Плохо: всё в одном классе
class ChemblPipeline:
    def fetch(self): ...
    def transform(self): ...
    def validate(self): ...
    def hash(self): ...
    def write_bronze(self): ...
    def write_silver(self): ...
    def manage_lock(self): ...
```

### ✓ Composition

```python
# Хорошо: композиция сервисов
class ChemblPipeline:
    def __init__(
        self,
        client: DataSourcePort,
        transformer: TransformerPort,
        validator: ValidatorPort,
        writer: SinkPort,
        lock: LockPort,
    ):
        ...
```

---

## Связи с другими документами

- **Domain Objects**: [01-domain-objects.md](01-domain-objects.md)
- **ETL Layers**: [02-etl-layers.md](02-etl-layers.md)
- **Physical Layout**: [05-physical-layout.md](05-physical-layout.md)
