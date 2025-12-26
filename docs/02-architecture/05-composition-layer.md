# Слой Composition (Композиция)

**Расположение:** `src/bioetl/composition/`

## 1. Назначение

Слой `Composition` (также известный как **Composition Root**) — это мозг системы сборки. Его единственная задача — соединить компоненты из разных слоев (`Domain`, `Application`, `Infrastructure`) в работающее приложение. 

Согласно архитектурному решению ADR-005, этот код был вынесен в отдельный слой, чтобы избавить слои `Interfaces` и `Application` от ответственности за создание конкретных реализаций адаптеров.

**Ключевые характеристики:**
- **Глобальная осведомленность:** Единственный слой (наряду с `Interfaces`), который "знает" обо всех остальных слоях. Ему разрешено импортировать из `infrastructure`, `application` и `domain`.
- **Сборка зависимостей:** Здесь происходит внедрение зависимостей (Dependency Injection).
- **Конфигурация:** Преобразует сырые настройки из YAML или переменных окружения в доменные объекты конфигурации.

## 2. Ключевые Компоненты

### 2.1. `bootstrap.py` — Процесс инициализации

Этот модуль содержит функции для высокоуровневой сборки основных сервисов:
- `bootstrap_pipeline()`: Основная точка входа для создания полностью готового к работе экземпляра пайплайна.
- Инициализация общих сервисов: Логгер, Метрики, Чекпоинты, Карантин.

### 2.2. `factories/` — Фабрики компонентов

В v5.1+ логика создания компонентов централизована в специализированных фабриках:

- **`GenericPipelineFactory`**: Универсальный конструктор пайплайнов. Декларативно описывает класс пайплайна, провайдер, схемы и класс трансформера для DI.
- **`HttpClientFactory`**: Создает настроенные `UnifiedHTTPClient` с учетом специфичных для каждого провайдера ограничений (Rate Limits, Circuit Breaker).
- **`StorageFactory`**: Собирает `StoragePort`, объединяя адаптеры для Bronze, Silver и Gold слоев.
- **`DataSourceFactory`**: Создает `DataSourcePort` для конкретного провайдера.

### 2.3. `providers/` — Реестр провайдеров

**Расположение:** `src/bioetl/composition/providers/`

Централизованная регистрация всех провайдеров данных:

- **`ProviderRegistry`**: Главный реестр провайдеров. Хранит конфигурацию каждого провайдера (data source creator, transformer class, pipelines).
- **`DataSourceRegistry`**: Фасад для backward compatibility. Делегирует создание в `ProviderRegistry`.

**Пример использования:**
```python
# Получение data source creator
creator = DataSourceRegistry.get("chembl")
data_source = creator(settings, config, logger)

# Или напрямую через ProviderRegistry
data_source = ProviderRegistry.create_data_source(
    "chembl", settings, config, logger
)
```

**Зарегистрированные провайдеры:**
| Provider | Data Sources | Pipelines |
|----------|--------------|-----------|
| chembl | ChemblAdapter | activity, assay, molecule, target, document, target_component |
| pubchem | PubChemAdapter | compound |
| uniprot | UniProtAdapter | protein |
| pubmed | PubMedAdapter | publications |

### 2.3. `registry.py` — Реестр пайплайнов

Предоставляет механизмы для динамического поиска и регистрации пайплайнов. Это позволяет CLI находить доступные пайплайны по их именам (например, `chembl_activity`).

## 3. Принципы Работы

- **Composition Root:** Вся логика создания объектов должна находиться как можно ближе к точке входа в приложение. В BioETL это `src/bioetl/composition/`.
- **Dependency Injection (DI):** Объекты никогда не создают свои зависимости сами. Если пайплайну нужен доступ к базе данных, он запрашивает `StoragePort` в конструкторе, а фабрика из слоя Composition предоставляет ему конкретную реализацию.
- **Декларативность:** Использование `GenericPipelineFactory` позволяет добавлять новые пайплайны простым объявлением в `pipeline_factories.py` без написания шаблонного кода сборки.
