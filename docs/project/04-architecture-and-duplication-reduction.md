# 04 Architecture and Duplication Reduction

## Цель

Минимизация дублирования кода и конфигураций через переиспользование компонентов, профилей и общих абстракций.

## Принципы

### 1. Иерархия конфигураций

**Проблема:** Повторяющиеся параметры в конфигах пайплайнов (pagination, client settings, storage paths).

**Решение:** Трехуровневая иерархия

```
configs/profiles/chembl_default.yaml   ← Базовые настройки для ChEMBL
      ↓ extends
configs/profiles/development.yaml      ← Профиль для dev
configs/profiles/production.yaml       ← Профиль для prod
      ↓ extends
configs/pipelines/chembl/activity.yaml ← Специфика entity
```

**Использование:**

```bash
# Development режим
bioetl run activity_chembl --profile development

# Production режим
bioetl run activity_chembl --profile production

# Override конкретного параметра
bioetl run activity_chembl --profile production --set client.timeout=120
```

### 2. Базовые компоненты для пайплайнов

**Иерархия пайплайнов:**

```
PipelineBase (docs/02-pipelines/00-pipeline-base.md)
  ↓ наследуется
ChemblBasePipeline (docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md)
  ↓ наследуется
ActivityPipeline, AssayPipeline, TargetPipeline, ...
```

**Что централизовано в PipelineBase:**
- Оркестрация стадий: extract → transform → validate → write
- Управление ресурсами (автоматическое `dispose()`)
- Атомарная запись результатов
- Dry-run режим
- Интеграция с логированием

**Что централизовано в ChemblBasePipeline:**
- Инициализация `ChemblExtractionService`
- Инициализация `ChemblWriteService`
- Валидация общих параметров ChEMBL (batch_size, cache_namespace)
- Хуки: `pre_transform()`, `domain_enrich()`

**Специфика в конкретных пайплайнах:**
- Только бизнес-логика трансформации
- Специфичная нормализация полей
- Уникальные правила валидации

### 3. Нормализация данных

**Проблема:** Дублирование логики нормализации в ActivityNormalizer, AssayNormalizer, TargetNormalizer.

**Решение:**

```
BaseChemblNormalizer (docs/02-pipelines/chembl/common/00-base-chembl-normalizer.md)
  ↓ используется
ActivityNormalizer
AssayNormalizer
TargetNormalizer
```

**BaseChemblNormalizer** выполняет:
- Приведение типов по `ColumnNormalizationSpec`
- Установку значений по умолчанию
- Вычисление хешей (hash_row, hash_business_key)
- Trim строк, нормализацию дат в UTC

**Специфичные Normalizer** добавляют только:
- Доменную логику (например, парсинг ligand_efficiency в Activity)
- Специфичные валидации (например, форматы ChEMBL ID)

### 4. Переиспользование ABC

**Политика:** Перед созданием нового компонента **обязательно** проверить, нет ли подходящего ABC.

**Реестры:**
- `src/bioetl/clients/base/abc_registry.yaml` — все ABC с описанием
- `src/bioetl/clients/base/abc_impls.yaml` — Default/Impl для каждого ABC

**Примеры переиспользования:**

| Задача | ABC | Default/Impl |
|--------|-----|--------------|
| Пагинация API | `PaginatorABC` | `OffsetPaginatorImpl` |
| Retry логика | `RetryPolicyABC` | `ExponentialBackoffRetryImpl` |
| Rate limiting | `RateLimiterABC` | `TokenBucketRateLimiterImpl` |
| Трансформация данных | `TransformerABC` | Создать специфичный Impl |
| Валидация | `ValidatorABC` | `PanderaValidatorImpl` |
| Запись данных | `WriterABC` | `UnifiedOutputWriter` |

### 5. Клиенты внешних API

**Проблема:** Каждый пайплайн может реализовать свою логику HTTP-запросов, retry, rate limiting.

**Решение:** Унификация через `UnifiedAPIClient` (docs/02-pipelines/03-unified-api-client.md)

```python
# ❌ Плохо: прямое использование requests в пайплайне
import requests
response = requests.get("https://api.chembl.org/...", timeout=30)

# ✅ Хорошо: использование UnifiedAPIClient
from bioetl.clients.unified import UnifiedAPIClient

client = UnifiedAPIClient(
    retry_policy=default_retry_policy(),
    rate_limiter=default_rate_limiter(),
    circuit_breaker=default_circuit_breaker()
)
response = client.fetch_one(request)
```

**UnifiedAPIClient** автоматически обеспечивает:
- Retry с exponential backoff
- Rate limiting
- Circuit breaker
- Таймауты
- Структурированное логирование

### 6. Схемы данных

**Проблема:** Повторение описания общих колонок (id, timestamps, chembl_release) в разных схемах.

**Решение:** Композиция базовых схем

```python
# Базовая схема для всех ChEMBL-сущностей
class BaseChemblSchema(pa.DataFrameModel):
    chembl_release: Series[str] = pa.Field(regex=r"^\d+$")
    extracted_at: Series[datetime] = pa.Field(coerce=True)
    hash_row: Series[str] = pa.Field(str_length=64)

# Специфичная схема наследует базовую
class ActivitySchema(BaseChemblSchema):
    activity_id: Series[int] = pa.Field(gt=0)
    molecule_chembl_id: Series[str] = pa.Field(regex=r"^CHEMBL\d+$")
    # ... остальные поля
```

**Преимущества:**
- Единое место для изменения базовых полей
- Гарантия единообразия метаданных
- Упрощение добавления новых схем

### 7. Отказ от избыточных слоёв

**Правило:** Не создавать новый слой/модуль, если задача решается расширением существующего.

**Чеклист перед созданием нового слоя:**
1. Можно ли разместить в существующем `core/`?
2. Можно ли добавить как Stage в Pipeline?
3. Можно ли реализовать через существующий ABC?
4. Можно ли использовать `PipelineHookABC` для расширения?

**Примеры:**

| Потребность | ❌ Не создавать | ✅ Использовать |
|-------------|----------------|-----------------|
| Сбор метрик | `MetricsCollector` слой | `PipelineHookABC` |
| Дополнительная валидация | `ValidationLayer` | `ValidatorABC` + `DQRuleABC` |
| Обогащение данных | `EnrichmentService` | `LookupEnricherABC` |
| Дедупликация | `DeduplicationModule` | `DeduplicatorABC` |

## Практические шаги при рефакторинге

### Шаг 1: Аудит дублирования

Запустить анализ:

```bash
# Поиск дублированных функций
grep -r "def normalize_" src/bioetl/pipelines/chembl/

# Поиск дублированных конфигов
diff configs/pipelines/chembl/activity.yaml configs/pipelines/chembl/assay.yaml
```

### Шаг 2: Вынос в базовые компоненты

Если находим дублированный код:

1. Проверить, есть ли подходящий ABC
2. Если есть → создать Impl и зарегистрировать в `abc_impls.yaml`
3. Если нет → оценить, нужен ли новый ABC или достаточно utility-функции в `core/`

### Шаг 3: Унификация конфигураций

1. Создать профиль с общими параметрами
2. Добавить `extends: profile_name` в пайплайновые конфиги
3. Удалить дублированные параметры из пайплайновых конфигов

### Шаг 4: Обновление тестов

После рефакторинга:

```bash
# Запуск тестов для проверки неизменности поведения
pytest tests/bioetl/pipelines/chembl/

# Golden-тесты для проверки детерминизма
pytest tests/golden/
```

## Метрики успеха

Отслеживать:

- **Код:** Lines of Code в пайплайнах должны снижаться при добавлении новых сущностей
- **Конфиги:** Количество строк в пайплайновых YAML должно быть минимальным
- **Тесты:** Coverage общих компонентов должен быть выше, чем специфичных
- **Документация:** Отношение страниц в `common/` к страницам в `entity/` должно расти

## Related Documents

- `docs/project/00-rules-summary.md` — общие правила проекта (включая политику ABC/Default/Impl, раздел 2)
- `docs/02-pipelines/00-pipeline-base.md` — базовый пайплайн
- `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md` — ChEMBL-базовый пайплайн
- `docs/02-pipelines/chembl/common/00-base-chembl-normalizer.md` — базовый нормализатор
- `docs/guides/configuration.md` — приоритеты конфигураций

