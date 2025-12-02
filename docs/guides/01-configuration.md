# 01 Configuration

## Структура YAML

Конфигурация пайплайнов строится на основе иерархической системы профилей и файлов конфигураций сущностей.

### Основные файлы

- `configs/pipelines/<provider>/<entity>.yaml`: Специфичная конфигурация для конкретного пайплайна (например, `chembl/activity.yaml`). Определяет `entity_name`, поля (`fields`), специфичные параметры `pipeline` и переопределения профилей.
- `configs/profiles/*.yaml`: Общие профили настроек (например, `chembl_default.yaml`, `development.yaml`, `production.yaml`).

### Механизм ConfigResolver

Класс `ConfigResolver` отвечает за сборку итоговой конфигурации:
1. **Загрузка**: Читает целевой файл конфигурации (например, `configs/pipelines/chembl/activity.yaml`).
2. **Наследование (`extends`)**: Если в конфиге указано поле `extends: <profile_name>`, загружается соответствующий профиль из `configs/profiles/`. Поддерживается рекурсивное наследование (профиль может наследовать другой профиль).
3. **Слияние**: Конфигурация пайплайна накладывается поверх базового профиля (Deep Merge).
4. **Overrides**: Аргументы CLI или специфичный профиль запуска (переданный через `--profile`) накладываются поверх результата.

## Секции конфигурации (PipelineConfig)

Основные секции, определяемые в профилях и конфигах:

- **provider / entity_name**: Идентификаторы пайплайна.
- **pagination**: Настройки пагинации (размер страницы, лимиты).
- **client**: Настройки HTTP-клиента (URL, таймауты, ретраи, rate limit).
- **storage**: Пути к директориям ввода/вывода (`output_path`, `cache_path`).
- **logging**: Уровни логирования и настройки структурированного вывода.
- **determinism**: Флаги для обеспечения воспроизводимости (`stable_sort`, `utc_timestamps`, `atomic_writes`).
- **qc**: Настройки контроля качества (генерация отчетов, пороги покрытия).
- **hashing**: Настройки генерации хешей (`business_key_fields` для дедупликации).
- **pipeline**: Специфичные параметры экстракции и фильтрации (например, `chembl_release`).
- **fields**: Описание полей схемы данных (используется для валидации и документации).

## Пример использования

**Профиль `configs/profiles/chembl_default.yaml`**:
```yaml
client:
  base_url: "https://www.ebi.ac.uk/chembl/api/data"
  rate_limit: 10.0
pagination:
  limit: 1000
hashing:
  business_key_fields: []
```

**Конфиг `configs/pipelines/chembl/activity.yaml`**:
```yaml
extends: chembl_default

entity_name: activity
pipeline:
  batch_size: 100

hashing:
  business_key_fields:
    - activity_id
    - molecule_chembl_id
```

При запуске `activity_chembl` настройки из `chembl_default` будут базой, а `activity.yaml` переопределит или дополнит их.
