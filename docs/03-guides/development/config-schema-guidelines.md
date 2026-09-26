______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Config Schema Guidelines

Руководство по работе со схемами конфигураций в BioETL.

*Версия: 1.0.0 | Дата: 2026-01-26*

______________________________________________________________________

## TL;DR

```python
# Импортируй из base_schemas для базовых классов
from bioetl.infrastructure.schemas.base_schemas import (
    BaseDQConfig,
    BaseCircuitBreakerConfig,
)

# Импортируй из pipeline_config для расширенных классов
from bioetl.infrastructure.schemas.pipeline_config import DQConfig, InputFilterConfig
```

______________________________________________________________________

## 1. Архитектура Схем Конфигураций

### 1.1. Иерархия Модулей

```
src/bioetl/infrastructure/schemas/
├── base_schemas.py      # Базовые классы (Single Source of Truth)
├── pipeline_config.py   # Расширенные классы для pipeline YAML
├── source_config.py     # Классы для configs/providers/*.yaml
├── filter_config.py     # Классы для секций filters в configs/base|providers|entities
├── dq_config.py         # Классы для секций quality в configs/base|providers|entities
└── composite_config.py  # Классы для composite pipelines
```

### 1.2. Принцип Single Source of Truth

**Каждая конфигурационная структура определена ОДИН раз в `base_schemas.py`.**

Другие модули **наследуют** от базовых классов, а не дублируют поля:

```python
# base_schemas.py - ЕДИНСТВЕННОЕ определение полей
class BaseCircuitBreakerConfig(BaseModel):
    failure_threshold: int = Field(default=5, ge=1, le=20)
    recovery_timeout: int = Field(default=300, ge=60, le=3600)


# source_config.py - НАСЛЕДОВАНИЕ, не дублирование
class CircuitBreakerYamlConfig(BaseCircuitBreakerConfig):
    """Circuit breaker for source configs."""

    pass  # Поля наследуются автоматически
```

______________________________________________________________________

## 2. Базовые Классы (base_schemas.py)

### 2.1. DQ Configuration

| Класс              | Назначение                                  |
| ------------------ | ------------------------------------------- |
| `BaseDQThresholds` | Пороги `soft_fail`/`hard_fail` с валидацией |
| `BaseDQConfig`     | Расширяет thresholds + `strict_validation`  |

```python
from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig

config = BaseDQConfig(
    soft_fail_threshold=0.05,
    hard_fail_threshold=0.20,
    strict_validation=False,
)
domain_config = config.to_domain()
```

### 2.2. Resilience Configuration

| Класс                      | Назначение                          |
| -------------------------- | ----------------------------------- |
| `BaseCircuitBreakerConfig` | failure_threshold, recovery_timeout |
| `BaseRateLimitConfig`      | requests_per_second, burst          |
| `BaseClientConfig`         | timeout_sec, max_retries            |

### 2.3. Filter Configuration

| Класс                              | Назначение                                    |
| ---------------------------------- | --------------------------------------------- |
| `BaseInputFilterConfig`            | Input ID filtering (single/multi-column mode) |
| `BaseFilterColumnSchema`           | Column mapping for multi-column filtering     |
| `BaseGoldFiltersConfig`            | Gold layer filters (columns, ranges, etc.)    |
| `BaseGoldColumnFilterConfig`       | Column filter with operator support           |
| `BaseGoldRangeFilterConfig`        | Range filter (min/max)                        |
| `BaseGoldListLengthFilterConfig`   | List length filter                            |
| `BaseGoldListContainsFilterConfig` | List contains filter                          |

### 2.4. Other Configurations

| Класс                   | Назначение                                     |
| ----------------------- | ---------------------------------------------- |
| `BaseApiConfig`         | API connection (base_url, rate_limit, timeout) |
| `BaseCsvExportConfig`   | CSV export settings                            |
| `BaseMaintenanceConfig` | VACUUM and maintenance settings                |

______________________________________________________________________

## 3. Расширение Базовых Классов

### 3.1. Добавление Новых Полей

```python
from bioetl.infrastructure.schemas.base_schemas import BaseCircuitBreakerConfig


class ExtendedCircuitBreakerConfig(BaseCircuitBreakerConfig):
    """Extended circuit breaker with additional fields."""

    # Новые поля
    alert_on_open: bool = Field(default=False)
    max_half_open_attempts: int = Field(default=3, ge=1, le=10)
```

### 3.2. Переопределение Валидаторов

```python
from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig
from pydantic import model_validator


class StrictDQConfig(BaseDQConfig):
    """Stricter DQ config for production."""

    @model_validator(mode="after")
    def validate_strict_mode(self) -> StrictDQConfig:
        if self.strict_validation and self.hard_fail_threshold > 0.10:
            raise ValueError("strict mode requires hard_fail <= 0.10")
        return self
```

### 3.3. Переопределение to_domain()

```python
class CustomDQConfig(BaseDQConfig):
    """Custom DQ config with additional processing."""

    def to_domain(self) -> DomainDQConfig:
        # Custom logic before conversion
        result = super().to_domain()
        # Custom logic after conversion
        return result
```

______________________________________________________________________

## 4. Паттерн to_domain()

Все схемы имеют метод `to_domain()` для конвертации в immutable domain objects:

```python
# Infrastructure schema (Pydantic, mutable)
pydantic_config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)

# Domain dataclass (frozen, immutable)
domain_config = pydantic_config.to_domain()

# domain_config теперь можно безопасно использовать в бизнес-логике
```

**Преимущества:**

- Чёткая граница между infrastructure (YAML parsing) и domain (business logic)
- Immutability в domain слое
- Валидация при конвертации

______________________________________________________________________

## 5. Правила Работы со Схемами

### 5.1. НЕ дублируй поля

❌ **Плохо:**

```python
# source_config.py
class RateLimitConfig(BaseModel):
    requests_per_second: float = 5.0  # Дублирование!
    burst: int = 10  # Дублирование!


# pipeline_config.py
class RateLimitSourceConfig(BaseModel):
    requests_per_second: float = 5.0  # То же самое!
    burst: int = 10  # То же самое!
```

✅ **Правильно:**

```python
# base_schemas.py
class BaseRateLimitConfig(BaseModel):
    requests_per_second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)


# source_config.py
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
        failure_threshold: Number of consecutive failures before opening circuit.
        recovery_timeout: Time in seconds before attempting recovery.
    """

    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of consecutive failures before opening circuit",
    )
```

### 5.4. Добавляй model_validator для cross-field validation

```python
@model_validator(mode="after")
def validate_thresholds(self) -> BaseDQThresholds:
    """Validate that soft_fail < hard_fail."""
    if self.soft_fail_threshold >= self.hard_fail_threshold:
        raise ValueError(
            f"soft_fail ({self.soft_fail_threshold}) must be < "
            f"hard_fail ({self.hard_fail_threshold})"
        )
    return self
```

> **Примечание:** `src/bioetl/infrastructure/schemas/base_schemas.py`
> сейчас является facade-модулем над provider-split реализациями. Стабильные
> импорты остаются на facade path, а не на внутренних split modules.

______________________________________________________________________

## 6. Миграция Существующего Кода

### 6.1. Обновление Импортов

```python
# Импортируй из base_schemas для базовых классов
from bioetl.infrastructure.schemas.base_schemas import BaseDQConfig

# Или из pipeline_config для расширенной версии:
from bioetl.infrastructure.schemas.pipeline_config import DQConfig
```

### 6.2. Проверка Inheritance

```python
# Проверь, что твой класс наследует от правильного базового
from bioetl.infrastructure.schemas.base_schemas import BaseCircuitBreakerConfig

assert issubclass(CircuitBreakerYamlConfig, BaseCircuitBreakerConfig)
```

______________________________________________________________________

## 7. Тестирование Схем

### 7.1. Тесты для Базовых Классов

```python
# tests/unit/infrastructure/schemas/test_base_schemas.py

def test-to_domain-conversion():
    """Verify domain conversion."""
    config = BaseDQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.25)
    domain = config.to_domain()

    assert domain.soft_fail_threshold == 0.10
    assert domain.hard_fail_threshold == 0.25
```

### 7.2. Тесты для Валидации

```python
def test_threshold_validation():
    """Verify threshold validation."""
    with pytest.raises(ValidationError):
        BaseDQThresholds(soft_fail_threshold=0.25, hard_fail_threshold=0.20)
```

______________________________________________________________________

## 8. Справочник Классов

| Модуль          | Класс                      | Базовый класс            | Назначение                      |
| --------------- | -------------------------- | ------------------------ | ------------------------------- |
| base_schemas    | `BaseDQThresholds`         | BaseModel                | DQ пороги                       |
| base_schemas    | `BaseDQConfig`             | BaseDQThresholds         | DQ конфиг                       |
| base_schemas    | `BaseCircuitBreakerConfig` | BaseModel                | Circuit breaker                 |
| base_schemas    | `BaseRateLimitConfig`      | BaseModel                | Rate limit                      |
| base_schemas    | `BaseClientConfig`         | BaseModel                | HTTP client                     |
| base_schemas    | `BaseApiConfig`            | BaseModel                | API connection                  |
| base_schemas    | `BaseCsvExportConfig`      | BaseModel                | CSV export                      |
| base_schemas    | `BaseInputFilterConfig`    | BaseModel                | Input filtering                 |
| base_schemas    | `BaseGoldFiltersConfig`    | BaseModel                | Gold filters                    |
| base_schemas    | `BaseMaintenanceConfig`    | BaseModel                | Maintenance                     |
| pipeline_config | `DQConfig`                 | -                        | Extended DQ (field validations) |
| pipeline_config | `CircuitBreakerConfig`     | BaseCircuitBreakerConfig | Pipeline CB                     |
| pipeline_config | `InputFilterConfig`        | BaseInputFilterConfig    | Pipeline input filter           |
| source_config   | `CircuitBreakerYamlConfig` | BaseCircuitBreakerConfig | Source CB                       |
| source_config   | `RateLimitYamlConfig`      | BaseRateLimitConfig      | Source rate limit               |
| filter_config   | `InputFilterFileConfig`    | BaseInputFilterConfig    | Standalone filter               |
| filter_config   | `GoldFiltersFileConfig`    | BaseGoldFiltersConfig    | Standalone gold filter          |

______________________________________________________________________

*Строй надёжно. Документируй честно. Не дублируй код.*
