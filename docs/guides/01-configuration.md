# Configuration Guide

Система конфигурации BioETL гибка и иерархична.

## Структура файлов

```text
configs/
├── profiles/               # Профили окружений
│   ├── chembl_default.yaml    # Базовые настройки ChEMBL
│   ├── development.yaml       # Настройки для разработки (быстро, дебаг)
│   └── production.yaml        # Настройки для продакшена (надежно, QC)
│
└── pipelines/             # Конфигурации конкретных сущностей
    └── chembl/
        ├── activity.yaml
        ├── assay.yaml
        └── ...
```

## Основные секции

### `pagination`
Управление размером выборки.
```yaml
pagination:
  limit: 1000       # Записей на страницу
  offset: 0         # Смещение
  max_pages: null   # Максимум страниц (null = все)
```

### `client`
Настройки HTTP-клиента.
```yaml
client:
  timeout: 30.0
  max_retries: 3
  rate_limit: 10    # Запросов в секунду
  backoff_factor: 2.0
```

### `determinism`
Настройки воспроизводимости.
```yaml
determinism:
  stable_sort: true
  utc_timestamps: true
  atomic_writes: true
```

### `qc`
Контроль качества.
```yaml
qc:
  enable_quality_report: true
  min_coverage: 0.8
```

## Наследование (extends)

Ключевое слово `extends` указывает на родительский конфиг. Параметры объединяются (merge), при этом дочерний конфиг имеет приоритет.

**Пример:** `activity.yaml` наследует `chembl_default.yaml` (или профиль, переданный через CLI, который сам наследует `chembl_default.yaml`).

