# Getting Started

## Требования
- Python 3.11+
- pip или poetry
- Доступ к интернету (для запросов к API ChEMBL)
- (Опционально) PostgreSQL для загрузки результатов (по умолчанию CSV/Parquet)

## Установка

Клонируйте репозиторий и установите зависимости:

```bash
git clone https://github.com/your-org/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
pip install -e .
```

## Первый запуск

### Smoke-тест
Для проверки работоспособности запустите пайплайн `activity_chembl` в режиме `development` с флагом `--dry-run`. Это выполнит extract, transform и validate на небольшом объеме данных (100 записей) без записи на диск.

```bash
bioetl run activity_chembl --profile development --dry-run
```

### Полный прогон
Для выполнения полноценного сбора данных используйте профиль `production` и укажите выходную директорию:

```bash
bioetl run activity_chembl --profile production -o output/activity/
```

## Структура выходных файлов
После успешного выполнения в `output/activity/` появятся:

```text
output/activity/
├── activity.csv                  # Основная таблица данных
├── meta.yaml                     # Метаданные запуска (версия, checksums, row_count)
├── quality_report_table.csv      # Отчет по качеству данных (пропуски, уникальность)
└── correlation_report_table.csv  # Корреляционный анализ числовых полей
```

## Следующие шаги
- Настройка параметров запуска: [Configuration](../guides/01-configuration.md)
- Запуск других пайплайнов: [Running Pipelines](../guides/00-running-pipelines.md)

