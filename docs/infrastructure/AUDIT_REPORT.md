# Аудит инфраструктурного слоя BioETL

**Дата:** 2025-12-10
**Версия:** 1.0
**Анализируемая директория:** `src/bioetl/infrastructure/`

## Резюме

Проведён анализ 68 Python-файлов в директории `src/bioetl/infrastructure/`. Выявлен ряд проблем с дублированием компонентов, нарушениями архитектурных принципов и техническим долгом.

**Статистика проблем:**
- Критичные: 3
- Желательно исправить: 9
- Косметические: 3

---

## Критичные проблемы

### 1. Дублирование Provider Registry Loaders

**Файлы:**
- `infrastructure/config/provider_registry_loader.py`
- `infrastructure/clients/provider_registry_loader.py`

**Проблема:** Два файла с почти идентичным назначением и частично перекрывающейся логикой:
- Оба имеют `ProviderRegistryError`, `ProviderNotConfiguredError`
- Оба загружают `providers.yaml` и валидируют структуру
- Оба определяют `ProviderRegistryEntryConfig/Model` (почти идентичные Pydantic модели)

**Использование:**
```python
# infrastructure/config/provider_registry_loader.py используется в:
infrastructure/config/loader.py:19

# infrastructure/clients/provider_registry_loader.py используется в:
interfaces/rest/server.py:21
interfaces/cli/app.py:19
```

**Рекомендация:** Объединить в единый модуль, вынести в `infrastructure/config/` или `infrastructure/providers/`.

---

### 2. Жёсткая привязка к ActivityRawModel в парсере/extraction service

**Файлы:**
- `infrastructure/clients/chembl/response_parser.py:6,14,18,21`
- `infrastructure/clients/chembl/impl/chembl_extraction_service_impl.py:16,167,187,191-192`

**Проблема:** `ChemblResponseParserImpl` и `ChemblExtractionServiceImpl` жёстко типизированы на `ActivityRawModel`, хотя должны обрабатывать разные сущности (molecule, target, assay, document).

```python
# response_parser.py
class ChemblResponseParserImpl(ResponseParserABC[ActivityRawModel]):
    def parse(self, raw_response: dict[str, object]) -> list[ActivityRawModel]:
        ...
        return [ActivityRawModel.model_validate(item) for item in value]
```

**Нарушение:** Это нарушает принцип единой ответственности и делает код негибким для других сущностей.

**Рекомендация:** Сделать парсер generic с параметром типа модели или использовать фабрику парсеров по entity.

---

### 3. Дублирование entity aliasing логики

**Файлы:**
- `infrastructure/clients/chembl/impl/chembl_http_client_impl.py:218-227`
- `infrastructure/clients/chembl/impl/chembl_extraction_service_impl.py:124-130`

**Проблема:** Идентичный маппинг entity -> endpoint продублирован:
```python
aliases = {
    "activity": "activity",
    "assay": "assay",
    "target": "target",
    "publication": "document",
    "molecule": "molecule",
}
```

**Рекомендация:** Вынести в единое место (например, `infrastructure/clients/chembl/constants.py` или domain config).

---

## Желательно исправить

### 4. Неиспользуемые компоненты

#### 4.1 FileCacheImpl
**Файл:** `infrastructure/clients/base/impl/cache.py:60-114`

Реализация файлового кэша не используется. Рекомендация: оценить необходимость; если не нужен — удалить.

#### 4.2 UnifiedAPIClientImpl
**Файл:** `infrastructure/clients/base/impl/unified_api_client_impl.py`

Класс дублирует функциональность `_HttpTransport` и является тонкой обёрткой. Рекомендация: удалить и использовать `_HttpTransport` напрямую.

#### 4.3 RenameColumnsConverter как класс
**Файл:** `infrastructure/output/converters/rename_columns_converter.py`

Дублирует логику из `factories.py`. Рекомендация: использовать только одну реализацию.

---

### 5. Дублирование логики в Normalization Services

**Файлы:**
- `infrastructure/transform/impl/chembl_normalization_service_impl.py`
- `infrastructure/transform/impl/default_normalization_transformer_impl.py`

Оба класса содержат почти идентичные методы (`apply_normalize`, `apply_normalize_dataframe`, `apply_normalize_series`, `apply_normalize_batch`).

Дополнительно в `normalize.py` определены 4 алиаса для одного класса:
```python
DefaultNormalizationTransformerImpl = DefaultNormImpl
NormalizationTransformer = DefaultNormImpl
NormalizationServiceImpl = DefaultNormImpl
NormalizationService = DefaultNormImpl
```

**Рекомендация:** Объединить или чётко разграничить ответственности, убрать избыточные алиасы.

---

### 6. Дублирование фабрик логгирования

**Файлы:**
- `infrastructure/observability/factories.py:31-34` → `default_logging_port()`
- `infrastructure/logging/factories.py:13-18` → `default_logger()`

Обе функции создают `StructuredLoggerImpl`. Рекомендация: оставить одну фабрику.

---

### 7. Дублирование метрик HTTP-клиента

**Файл:** `infrastructure/observability/metrics.py`

Определены 2 набора похожих метрик с разными naming conventions (`bioetl_*` и без префикса). Рекомендация: унифицировать.

---

### 8. Backward-compatibility shims

**Файлы:**
- `infrastructure/config/models.py` — только re-export из `domain.configs`
- `infrastructure/files/csv_record_source.py` — lazy shim в application слой

**Рекомендация:** Постепенно мигрировать, затем удалить.

---

## Косметические замечания

### 9. Смешение языков в документации

Комментарии и docstrings на русском и английском. Рекомендация: стандартизировать на английском.

### 10. Избыточные методы-алиасы

В request_builder, response_parser, paginator много методов-дубликатов (`for_endpoint` → `build_for_endpoint` и т.п.).

### 11. Непоследовательность именования

Смешаны суффиксы `*Impl`, `*Factory`, двойные алиасы класс + переменная.

---

## Нарушения DDD/архитектурных принципов

### Утечка доменных моделей в infrastructure

- `response_parser.py` импортирует `ActivityRawModel` из domain/schemas
- `extraction_service_impl.py` возвращает `ActivityRawModel`
- `config/loader.py` использует `register_schemas`, `get_pipeline_contract`

### Бизнес-логика в extraction service

`_attach_entity_fields` в `chembl_extraction_service_impl.py:66-84` — логика обогащения фильтров полями является application/domain concern.

### Service Locator anti-pattern

`_HttpTransport` создаёт зависимости внутри себя через default fallbacks.

---

## План рефакторинга

### Высокий приоритет (Quick Wins)

| # | Задача | Файлы |
|---|--------|-------|
| 1 | Объединить provider_registry_loader | 2 файла → 1 |
| 2 | Удалить UnifiedAPIClientImpl | 1 файл |
| 3 | Вынести entity aliases в константы | 2 файла |
| 4 | ~~Удалить CircuitBreakerImpl~~ | ✅ Выполнено |

### Средний приоритет

| # | Задача | Файлы |
|---|--------|-------|
| 5 | Унифицировать normalization services | 2+ файлов |
| 6 | Унифицировать метрики | 1 файл |
| 7 | Удалить shims | 2 файла |
| 8 | Generic response parser | 2 файла |

### Низкий приоритет

| # | Задача |
|---|--------|
| 9 | Унифицировать docstrings на английский |
| 10 | Убрать алиасы методов |
| 11 | Стандартизировать naming |
| 12 | Удалить неиспользуемый FileCacheImpl |

---

## Матрица зависимостей Infrastructure → Domain

| Infrastructure компонент | Domain зависимости |
|-------------------------|-------------------|
| config/loader.py | schemas, configs, errors, validation |
| clients/chembl/*.py | schemas.chembl.raw_models, configs, contracts |
| output/*.py | models.RunContext, configs.QcConfig |
| transform/*.py | transform.contracts, transform.normalizers |
| validation/*.py | schemas.registry, validation.contracts |

---

## Допущения

1. Предполагается, что проект следует Hexagonal Architecture (судя по ADR-0001)
2. Предполагается, что ChEMBL — основной (но не единственный) провайдер данных
3. При анализе использования компонентов учитывались только файлы в `src/`, тесты не анализировались на предмет использования
