# Issue: Параметры из config файлов не используются (hardcode)

**Приоритет:** Medium
**Дата:** 2024-12-29
**Статус:** Open

## Описание проблемы

Анализ кодовой базы выявил, что **~40% параметров из config файлов не используются** — вместо них применяются hardcoded значения.

## Параметры, которые НЕ используются

### 1. Source configs (`configs/sources/*.yaml`) — полностью игнорируются

| YAML параметр | Ожидаемое значение | Hardcode в коде |
|---------------|-------------------|-----------------|
| `source.rate_limit.requests_per_second` | chembl: 5 | `registration.py:276`: `rate=10.0` |
| `source.rate_limit.burst` | chembl: 10 | `registration.py:277`: `capacity=20` |
| `source.circuit_breaker.failure_threshold` | 5 | `http_client_factory.py:111,132`: default 5 |
| `source.circuit_breaker.recovery_timeout` | 300 | `http_client_factory.py:111,132`: default 300 |
| `source.provider_config.timeout_sec` | 30.0 | `http/client.py:84`: hardcoded |
| `source.provider_config.batch_size` | 20 | `chembl/client.py:71`: `batch_size=1000` |
| `source.provider_config.max_retries` | 3 | Не передаётся |

### 2. Pipeline circuit_breaker не конвертируется

```yaml
# configs/pipelines/_defaults.yaml:27-29
circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 300
```

`PipelineYamlConfig.circuit_breaker.to_domain()` существует (`schemas/pipeline_config.py:88-97`), но **никогда не вызывается** при создании CircuitBreaker.

### 3. Rate limits hardcoded в ProviderRegistry

| Файл | Строка | Provider | Hardcoded | YAML config |
|------|--------|----------|-----------|-------------|
| `registration.py` | 276-277 | ChEMBL | `rate=10.0, capacity=20` | `5 req/s, burst=10` |
| `registration.py` | 294-295 | PubChem | `rate=5.0, capacity=10` | — |
| `registration.py` | 311-312 | UniProt | `rate=10.0, capacity=20` | — |
| `registration.py` | 328-329 | PubMed | `rate=3.0, capacity=6` | — |

### 4. Adapter batch_size defaults

| Файл | Строка | Hardcode | Должно быть |
|------|--------|----------|-------------|
| `chembl/client.py` | 71 | `batch_size=1000` | из `source.batch_size` (20) |
| `chembl/client.py` | 303 | `batch_size=100` | из config |
| `pubmed/pubmed_client.py` | 53 | `batch_size=200` | из config |
| `crossref/client.py` | 64 | `batch_size=50` | из config |

## Параметры, которые работают корректно ✓

- `dq_rules.soft_fail_threshold` / `hard_fail_threshold` → `infrastructure/config.py:273`
- `gold_filters.*` → `infrastructure/config.py:263`
- `sink.silver.mode` / `sink.gold.mode` → `infrastructure/config.py:224-231`
- `sink.silver.on_schema_mismatch` → `infrastructure/config.py:266-270`
- `input_filter.*` → `schemas/pipeline_config.py:136-152`
- `primary_keys`, `silver_table`, `batch_size` (pipeline level)
- `source.api_key`, `source.email` (PubMed) → `registration.py:233-239`
- `source.api.base_url` (UniProt) → `registration.py:214`

## План исправления

### Фаза 1: Загрузка source config

- [ ] Добавить функцию `load_source_config(provider: str)` в `infrastructure/config.py`
- [ ] Создать Pydantic schema `SourceYamlConfig` для валидации `configs/sources/*.yaml`
- [ ] Парсить source config при создании data source

### Фаза 2: Передача параметров в factories

- [ ] `HttpClientFactory.create_for_provider()` — принимать `source_config` параметр
- [ ] Использовать `source_config.rate_limit.requests_per_second` вместо hardcoded
- [ ] Использовать `source_config.rate_limit.burst` для capacity
- [ ] Передавать `circuit_breaker.failure_threshold` и `recovery_timeout` в `CircuitBreaker()`

### Фаза 3: Adapter batch_size

- [ ] `DataSourceFactory.create()` — передавать `batch_size` из source config
- [ ] Убрать hardcoded `batch_size=1000` default в ChemblAdapter
- [ ] Убрать hardcoded batch_size в других адаптерах

### Фаза 4: Унификация ProviderRegistry

- [ ] Удалить hardcoded `HttpConfig(rate=..., capacity=...)` из `registration.py`
- [ ] ProviderRegistry должен загружать config из YAML при регистрации
- [ ] Или: передавать source_config при вызове `create_for_provider()`

### Фаза 5: Тесты

- [ ] Добавить тест `test_source_config_used_not_hardcoded` в `tests/architecture/`
- [ ] Проверять, что rate limit из YAML применяется
- [ ] Проверять, что circuit breaker параметры из YAML применяются

## Затронутые файлы

**Требуют изменений:**
- `src/bioetl/composition/providers/registration.py` — убрать hardcoded rate limits
- `src/bioetl/composition/factories/http_client_factory.py` — использовать config
- `src/bioetl/infrastructure/adapters/chembl/client.py` — batch_size из config
- `src/bioetl/infrastructure/config.py` — добавить load_source_config()

**Для справки (конфиги):**
- `configs/sources/chembl.yaml`
- `configs/sources/pubchem.yaml`
- `configs/sources/uniprot.yaml`
- `configs/sources/pubmed.yaml`
- `configs/pipelines/_defaults.yaml`

## Примечания

Функциональность работает с default значениями, но пользователь не может изменить поведение через конфигурацию — изменения в YAML файлах игнорируются.
