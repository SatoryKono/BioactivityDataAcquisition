# 01 Getting Started

## Системные требования
- Python 3.10+.
- Установка зависимостей из `requirements.txt` или `pyproject.toml` (виртуальное окружение рекомендовано).
- Доступ к исходным REST-API (ChEMBL и др.) и сети для скачивания данных; локальная БД не обязательна, вывод формируется в файловой системе.
- Достаточно дискового пространства для артефактов (таблицы CSV/Parquet, QC-отчёты, meta.yaml).

## Установка проекта
1. Клонируйте репозиторий:
   ```bash
   git clone <repo-url>
   cd BioactivityDataAcquisition
   ```
2. Создайте и активируйте виртуальное окружение.
3. Установите зависимости:
   ```bash
   pip install -e .
   ```
4. При необходимости настройте переменные окружения для ключей API (см. `docs/guides/01-configuration.md`).

## Запуск пайплайна через CLI
Пример запуска ChEMBL Activity-пайплайна в стандартном профиле:
```bash
bioetl run --pipeline chembl_activity --config configs/pipelines/chembl/activity.yaml
```
Дополнительно можно указать профиль (`--profile dev|prod`), режим `--dry-run` и каталог вывода `--output-dir <path>`.

## Структура выходных артефактов
После успешного запуска в каталоге результата формируется структура:
```
<output_dir>/
  tables/
    activity_table.csv|parquet
    ... другие таблицы
  meta.yaml
  qc/
    quality_report_table.csv
    correlation_report_table.csv
  checksums/
    activity_table.sha256
```
- Таблицы хранят нормализованные данные.
- `meta.yaml` фиксирует версию пайплайна, источник данных, размер выборки и контрольные суммы.
- QC-отчёты содержат агрегаты и корреляции для быстрых проверок качества.
