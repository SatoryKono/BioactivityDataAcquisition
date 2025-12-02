# Bioactivity Data Acquisition (BioETL)

ETL-фреймворк для извлечения, нормализации и интеграции данных биологической активности из научных REST API (ChEMBL, PubMed, PubChem и др.).

## Документация

Полная документация доступна в директории `docs/`:

- **[Overview](docs/overview/00-index.md)**: Введение, быстрый старт, глоссарий.
- **[Architecture](docs/architecture/00-index.md)**: Принципы архитектуры, слои, поток данных.
- **[ABC Reference](docs/reference/abc/00-index.md)**: Каталог интерфейсов.
- **[Pipelines](docs/02-pipelines/chembl/00-index.md)**: Описание ETL-пайплайнов ChEMBL.
- **[Guides](docs/guides/00-running-pipelines.md)**: Руководства по запуску и конфигурации.

## Быстрый старт

```bash
# Установка
pip install -e .

# Запуск smoke-теста
bioetl run activity_chembl --profile development --dry-run
```

## Лицензия

MIT

