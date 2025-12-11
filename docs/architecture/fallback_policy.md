# Fallback Policy: Configuration Defaults Resolution

**Версия:** 1.0
**Дата:** 2025-12-11

---

## Обзор

Данный документ описывает политику разрешения (fallback policy) для конфигурационных значений по умолчанию в BioactivityDataAcquisition. Политика обеспечивает предсказуемое поведение системы при отсутствии явно заданных параметров.

---

## Архитектурные принципы

### 1. Иерархия приоритетов (от высшего к низшему)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Явно заданные значения в конфигурации пайплайна        │
│     (configs/pipelines/*.yaml)                              │
├─────────────────────────────────────────────────────────────┤
│  2. Переопределения через переменные окружения              │
│     (BIOETL_*, ${VAR} в YAML)                               │
├─────────────────────────────────────────────────────────────┤
│  3. Централизованные defaults (configs/defaults/*.yaml)     │
│     Загружаются через DefaultsConfig                        │
├─────────────────────────────────────────────────────────────┤
│  4. Hardcoded defaults в domain/configs/*.py                │
│     (Field defaults в Pydantic моделях)                     │
└─────────────────────────────────────────────────────────────┘
```

### 2. Места определения defaults

| Слой | Файл | Тип | Назначение |
|------|------|-----|------------|
| **Domain** | `domain/configs/defaults.py` | Pydantic models | Структура и валидация defaults |
| **Domain** | `domain/configs/pipeline.py` | Field defaults | Hardcoded значения по умолчанию |
| **Infrastructure** | `infrastructure/config/defaults_loader.py` | Loader | Загрузка YAML defaults |
| **Infrastructure** | `configs/defaults/*.yaml` | YAML files | Централизованные defaults |
| **Composition** | `interfaces/composition_root.py` | Factory defaults | Runtime defaults для DI |

---

## Компоненты политики

### DefaultsConfig (domain/configs/defaults.py)

Агрегатор всех конфигураций по умолчанию:

```python
class DefaultsConfig(BaseModel):
    hashing: HashingDefaultsConfig      # Параметры хеширования
    normalization: NormalizationDefaultsConfig  # Нормализация данных
    network: NetworkDefaultsConfig | None  # HTTP настройки
    sources: dict[str, SourceDefaultsConfig]  # Per-provider defaults
```

### Загрузка defaults (infrastructure/config/defaults_loader.py)

```python
def get_defaults_config(*, base_dir: str | Path | None = None) -> DefaultsConfig:
    """
    Порядок поиска:
    1. base_dir (если указан)
    2. BIOETL_CONFIG_DIR (переменная окружения)
    3. DEFAULT_CONFIGS_ROOT (package default)
    """
```

### Fallback для отсутствующих файлов

```python
def _select_defaults_root(primary: Path, fallback: Path) -> Path:
    """
    1. Проверяет primary (пользовательский путь)
    2. Если нет — использует fallback (package defaults)
    3. Если оба отсутствуют — DefaultsFileNotFoundError
    """
```

---

## Практические примеры

### Пример 1: HTTP Client Configuration

```yaml
# configs/defaults/network.yaml
http:
  default:
    max_url_length: 8000
  http:
    timeout_sec: 30
    max_retries: 3
    rate_limit: 5.0
```

Порядок разрешения для `timeout_sec`:

1. `pipeline.yaml: http.timeout_sec: 60` → **60**
2. `$BIOETL_HTTP_TIMEOUT` → из переменной окружения
3. `defaults/network.yaml: http.http.timeout_sec: 30` → **30**
4. `HttpClientConfig.timeout_sec: int = 30` → hardcoded **30**

### Пример 2: Provider-specific Defaults

```yaml
# configs/defaults/sources.yaml
sources:
  chembl:
    provider: chembl
    base_url: https://www.ebi.ac.uk/chembl/api/data
    batch_size: 1000
    max_url_length: 8000
```

```python
# В коде
defaults = get_defaults_config()
chembl_defaults = defaults.get_source_default("chembl")
batch_size = chembl_defaults.batch_size if chembl_defaults else 500
```

### Пример 3: Hashing Configuration

```yaml
# configs/hashing.yaml
hashing:
  algorithm: sha256
  include_columns: null  # All columns
  exclude_columns:
    - acquisition_timestamp
    - database_version
```

---

## Правила разрешения конфликтов

### 1. Explicit over Implicit

Явно заданное значение всегда имеет приоритет:

```python
# В PipelineConfig
if config.http is not None:
    return config.http.timeout_sec  # Explicit
return defaults.network.http.http.timeout_sec  # Fallback
```

### 2. Environment over File

Переменные окружения переопределяют файлы:

```yaml
# configs/defaults/network.yaml
http:
  http:
    timeout_sec: ${BIOETL_HTTP_TIMEOUT:-30}  # 30 если переменная не задана
```

### 3. Specific over Generic

Provider-specific defaults имеют приоритет над generic:

```python
def get_batch_size(provider: str) -> int:
    source_default = defaults.get_source_default(provider)
    if source_default and source_default.batch_size:
        return source_default.batch_size  # Provider-specific
    return DEFAULT_BATCH_SIZE  # Generic fallback
```

---

## Композиция в runtime (CompositionRoot)

### Factory Defaults

```python
class CompositionRoot:
    def __init__(
        self,
        *,
        observability_factory: ObservabilityFactoryABC | None = None,
        infrastructure_factory: InfrastructureFactoryABC | None = None,
    ):
        # Fallback to default factories
        self._observability = observability_factory or DefaultObservabilityFactory()
        self._infrastructure = infrastructure_factory or DefaultInfrastructureFactory()
```

### Lazy Initialization

```python
def get_provider_registry(self) -> ProviderRegistryABC:
    if self._provider_registry is None:
        # Lazy fallback: create only when needed
        registry_factory = create_provider_registry_factory()
        self._provider_registry = registry_factory()
    return self._provider_registry
```

---

## Тестирование fallback policy

### Unit Tests

```python
def test_defaults_fallback_to_hardcoded():
    """Test that missing YAML defaults use hardcoded values."""
    # Clear cached defaults
    _load_defaults_cached.cache_clear()

    # Create config without network section
    config = DefaultsConfig(
        hashing=HashingDefaultsConfig(...),
        normalization=NormalizationDefaultsConfig(...),
        network=None,  # Missing
        sources={},
    )

    # Verify fallback to hardcoded
    assert config.network is None
    # Application layer should use HttpClientConfig defaults
```

### Integration Tests

```python
def test_env_override_file_defaults(monkeypatch):
    """Test environment variable overrides file defaults."""
    monkeypatch.setenv("BIOETL_HTTP_TIMEOUT", "120")

    defaults = get_defaults_config()
    # Should use env value, not file value
    assert defaults.network.http.http.timeout_sec == 120
```

---

## Диагностика

### Logging

При загрузке defaults логируются источники:

```python
logger.debug(f"Loading defaults from: {root}")
logger.debug(f"Fallback to package defaults: {DEFAULT_CONFIGS_ROOT}")
```

### Ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `DefaultsFileNotFoundError` | Отсутствует обязательный файл | Создать файл или проверить путь |
| `DefaultsValidationError` | Невалидный YAML | Проверить структуру YAML |
| `KeyError: 'hashing'` | Отсутствует root key | Добавить обязательную секцию |

---

## Checklist для добавления новых defaults

1. [ ] Определить Pydantic модель в `domain/configs/defaults.py`
2. [ ] Добавить Field defaults для hardcoded значений
3. [ ] Создать YAML файл в `configs/defaults/`
4. [ ] Обновить `_load_defaults_cached()` для загрузки
5. [ ] Документировать переменные окружения
6. [ ] Добавить тесты fallback поведения

---

## Ссылки

- `src/bioetl/domain/configs/defaults.py` — Domain models
- `src/bioetl/infrastructure/config/defaults_loader.py` — Loader
- `configs/defaults/` — YAML defaults
- `src/bioetl/interfaces/composition_root.py` — Runtime composition
