# Running Pipelines

Руководство по запуску ETL-пайплайнов с использованием интерфейса командной строки (CLI).

## Основной синтаксис

```bash
bioetl run [PIPELINE_NAME] [OPTIONS]
```

## Примеры использования

### 1. Разработка (Smoke Test)
Быстрый запуск для проверки логики. Используется профиль `development` (маленькие лимиты) и флаг `--dry-run` (без записи).

```bash
bioetl run activity_chembl --profile development --dry-run
```

### 2. Продакшн (Full Run)
Полный сбор данных. Используется профиль `production` (стандартные лимиты, включенный QC).

```bash
bioetl run activity_chembl --profile production -o output/activity_2024/
```

### 3. Переопределение параметров
Можно точечно менять настройки "на лету" без правки YAML-файлов.

```bash
# Увеличить таймаут и лимит страниц
bioetl run activity_chembl \
  --set client.timeout=60 \
  --set pagination.limit=500 \
  --set pagination.max_pages=20
```

## Программный запуск

Пайплайны можно запускать из Python-кода (например, из Airflow или Jupyter).

```python
from pathlib import Path
from bioetl.config import load_config
from bioetl.pipelines.chembl.activity.run import ChemblActivityPipeline

# 1. Загрузка конфигурации
config = load_config("configs/pipelines/chembl/activity.yaml", profile="production")

# 2. Инициализация пайплайна
pipeline = ChemblActivityPipeline(config, run_id="manual_run_001")

# 3. Запуск
result = pipeline.run(output_dir=Path("output/activity"))

print(f"Pipeline finished: {result.status}")
print(f"Rows processed: {result.row_count}")
```

