# Config Schema Guidelines

Руководство по работе со схемами конфигураций в BioETL.

*Версия: 1.0.0 | Дата: 2026-01-26*

---

## TL;DR

```python
# Импортируй из base-schemas для базовых классов
from bioetl.infrastructure.schemas.base-schemas import BaseDQConfig, BaseCircuitBreakerConfig

# Импортируй из pipeline-config для расширенных классов
from bioetl.infrastructure.schemas.pipeline-config import DQConfig, InputFilterConfig
```

---

## 1. Архитектура Схем Конфигураций

### 1.1. Иерархия Модулей

```
src/bioetl/infrastructure/schemas/
├── base-schemas.py      # Базовые классы (Single Source of Truth)
├── pipeline-config.py   # Расширенные классы для pipeline YAML
├── source-config.py     # Классы для configs/providers/*.yaml
├── filter-config.py     # Классы для configs/filters/*.yaml
├── dq-config.py         # Классы для configs/quality/*.yaml
└── composite-config.py  # Классы для composite pipelines
```

### 1.2. Принцип Single Source of Truth

**Каждая конфигурационная структура определена ОДИН раз в `base-schemas.py`.**

Другие модули **наследуют** от базовых классов, а не дублируют поля:

```python
# base-schemas.py - ЕДИНСТВЕННОЕ определение полей
class BaseCircuitBreakerConfig(BaseModel):
    failure-threshold: int = Field(default=5, ge=1, le=20)
    recovery-timeout: int = Field(default=300, ge=60, le=3600)

# source-config.py - НАСЛЕДОВАНИЕ, не дублирование
class CircuitBreakerYamlConfig(BaseCircuitBreakerConfig):
    """Circuit breaker for source configs."""
    pass  # Поля наследуются автоматически
```

---

## 2. Базовые Классы (base-schemas.py)

### 2.1. DQ Configuration

| Класс | Назначение |
|-------|------------|
| `BaseDQThresholds` | Пороги soft-fail/hard-fail с валидацией |
| `BaseDQConfig` | Расширяет Thresholds + strict-validation |

```python
from bioetl.infrastructure.schemas.base-schemas import BaseDQConfig

config = BaseDQConfig(
    soft-fail-threshold=0.05,
    hard-fail-threshold=0.20,
    strict-validation=False,
)
domain-config = config.to-domain()
```

### 2.2. Resilience Configuration

| Класс | Назначение |
|-------|------------|
| `BaseCircuitBreakerConfig` | failure-threshold, recovery-timeout |
| `BaseRateLimitConfig` | requests-per-second, burst |
| `BaseClientConfig` | timeout-sec, max-retries |

### 2.3. Filter Configuration

| Класс | Назначение |
|-------|------------|
| `BaseInputFilterConfig` | Input ID filtering (single/multi-column mode) |
| `BaseFilterColumnSchema` | Column mapping for multi-column filtering |
| `BaseGoldFiltersConfig` | Gold layer filters (columns, ranges, etc.) |
| `BaseGoldColumnFilterConfig` | Column filter with operator support |
| `BaseGoldRangeFilterConfig` | Range filter (min/max) |
| `BaseGoldListLengthFilterConfig` | List length filter |
| `BaseGoldListContainsFilterConfig` | List contains filter |

### 2.4. Other Configurations

| Класс | Назначение |
|-------|------------|
| `BaseApiConfig` | API connection (base-url, rate-limit, timeout) |
| `BaseCsvExportConfig` | CSV export settings |
| `BaseMaintenanceConfig` | VACUUM and maintenance settings |

---

## 3. Расширение Базовых Классов

### 3.1. Добавление Новых Полей

```python
from bioetl.infrastructure.schemas.base-schemas import BaseCircuitBreakerConfig

class ExtendedCircuitBreakerConfig(BaseCircuitBreakerConfig):
    """Extended circuit breaker with additional fields."""

    # Новые поля
    alert-on-open: bool = Field(default=False)
    max-half-open-attempts: int = Field(default=3, ge=1, le=10)
```

### 3.2. Переопределение Валидаторов

```python
from bioetl.infrastructure.schemas.base-schemas import BaseDQConfig
from pydantic import model-validator

class StrictDQConfig(BaseDQConfig):
    """Stricter DQ config for production."""

    @model-validator(mode="after")
    def validate-strict-mode(self) -> StrictDQConfig:
        if self.strict-validation and self.hard-fail-threshold > 0.10:
            raise ValueError("strict mode requires hard-fail <= 0.10")
        return self
```

### 3.3. Переопределение to-domain()

```python
class CustomDQConfig(BaseDQConfig):
    """Custom DQ config with additional processing."""

    def to-domain(self) -> DomainDQConfig:
        # Custom logic before conversion
        result = super().to-domain()
        # Custom logic after conversion
        return result
```

---

## 4. Паттерн to-domain()

Все схемы имеют метод `to-domain()` для конвертации в immutable domain objects:

```python
# Infrastructure schema (Pydantic, mutable)
pydantic-config = DQConfig(soft-fail-threshold=0.05, hard-fail-threshold=0.20)

# Domain dataclass (frozen, immutable)
domain-config = pydantic-config.to-domain()

# domain-config теперь можно безопасно использовать в бизнес-логике
```

**Преимущества:**
- Чёткая граница между infrastructure (YAML parsing) и domain (business logic)
- Immutability в domain слое
- Валидация при конвертации

---

## 5. Правила Работы со Схемами

### 5.1. НЕ дублируй поля

❌ **Плохо:**
```python
# source-config.py
class RateLimitConfig(BaseModel):
    requests-per-second: float = 5.0  # Дублирование!
    burst: int = 10                   # Дублирование!

# pipeline-config.py
class RateLimitSourceConfig(BaseModel):
    requests-per-second: float = 5.0  # То же самое!
    burst: int = 10                   # То же самое!
```

✅ **Правильно:**
```python
# base-schemas.py
class BaseRateLimitConfig(BaseModel):
    requests-per-second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)

# source-config.py
class RateLimitYamlConfig(BaseRateLimitConfig):
    pass  # Наследуем все поля
```

### 5.2. Используй Field() для всех полей

❌ **Плохо:**
```python
class Config(BaseModel):
    timeout: int = 30  # Нет валидации!
```

✅ **Правильно:**
```python
class Config(BaseModel):
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
```

### 5.3. Документируй классы и поля

```python
class BaseCircuitBreakerConfig(BaseModel):
    """Base class for Circuit Breaker configuration.

    Provides common circuit breaker fields for both pipeline and source configs.

    Attributes:
        failure-threshold: Number of consecutive failures before opening circuit.
        recovery-timeout: Time in seconds before attempting recovery.
    """

    failure-threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of consecutive failures before opening circuit",
    )
```

### 5.4. Добавляй model-validator для cross-field validation

```python
@model-validator(mode="after")
def validate-thresholds(self) -> BaseDQThresholds:
    """Validate that soft-fail < hard-fail."""
    if self.soft-fail-threshold >= self.hard-fail-threshold:
        raise ValueError(
            f"soft-fail ({self.soft-fail-threshold}) must be < "
            f"hard-fail ({self.hard-fail-threshold})"
        )
    return self
```

---

## 6. Миграция Существующего Кода

### 6.1. Обновление Импортов

```python
# Импортируй из base-schemas для базовых классов
from bioetl.infrastructure.schemas.base-schemas import BaseDQConfig

# Или из pipeline-config для расширенной версии:
from bioetl.infrastructure.schemas.pipeline-config import DQConfig
```

### 6.2. Проверка Inheritance

```python
# Проверь, что твой класс наследует от правильного базового
from bioetl.infrastructure.schemas.base-schemas import BaseCircuitBreakerConfig

assert issubclass(CircuitBreakerYamlConfig, BaseCircuitBreakerConfig)
```

---

## 7. Тестирование Схем

### 7.1. Тесты для Базовых Классов

```python
# tests/unit/infrastructure/schemas/test-base-schemas.py

def test-to-domain-conversion():
    """Verify domain conversion."""
    config = BaseDQConfig(soft-fail-threshold=0.10, hard-fail-threshold=0.25)
    domain = config.to-domain()

    assert domain.soft-fail-threshold == 0.10
    assert domain.hard-fail-threshold == 0.25
```

### 7.2. Тесты для Валидации

```python
def test-threshold-validation():
    """Verify threshold validation."""
    with pytest.raises(ValidationError):
        BaseDQThresholds(soft-fail-threshold=0.25, hard-fail-threshold=0.20)
```

---

## 8. Справочник Классов

| Модуль | Класс | Базовый класс | Назначение |
|--------|-------|---------------|------------|
| base-schemas | `BaseDQThresholds` | BaseModel | DQ пороги |
| base-schemas | `BaseDQConfig` | BaseDQThresholds | DQ конфиг |
| base-schemas | `BaseCircuitBreakerConfig` | BaseModel | Circuit breaker |
| base-schemas | `BaseRateLimitConfig` | BaseModel | Rate limit |
| base-schemas | `BaseClientConfig` | BaseModel | HTTP client |
| base-schemas | `BaseApiConfig` | BaseModel | API connection |
| base-schemas | `BaseCsvExportConfig` | BaseModel | CSV export |
| base-schemas | `BaseInputFilterConfig` | BaseModel | Input filtering |
| base-schemas | `BaseGoldFiltersConfig` | BaseModel | Gold filters |
| base-schemas | `BaseMaintenanceConfig` | BaseModel | Maintenance |
| pipeline-config | `DQConfig` | - | Extended DQ (field validations) |
| pipeline-config | `CircuitBreakerConfig` | BaseCircuitBreakerConfig | Pipeline CB |
| pipeline-config | `InputFilterConfig` | BaseInputFilterConfig | Pipeline input filter |
| source-config | `CircuitBreakerYamlConfig` | BaseCircuitBreakerConfig | Source CB |
| source-config | `RateLimitYamlConfig` | BaseRateLimitConfig | Source rate limit |
| filter-config | `InputFilterFileConfig` | BaseInputFilterConfig | Standalone filter |
| filter-config | `GoldFiltersFileConfig` | BaseGoldFiltersConfig | Standalone gold filter |

---

*Строй надёжно. Документируй честно. Не дублируй код.*
