# Bioactivity Data Acquisition (BioETL)

ETL-фреймворк для извлечения, нормализации и интеграции данных биологической активности из научных REST API (ChEMBL, PubMed, PubChem и др.).

## Документация

Полная документация доступна в директории `docs/`:

- **[Map](docs/MAP.md)**: Навигатор по проекту (Docs ↔ Src ↔ Configs).
- **[Architecture](docs/architecture/00-index.md)**: Принципы архитектуры, слои, поток данных.
- **[Domain](docs/domain/glossary.md)**: Глоссарий и схемы данных.
- **[Pipelines](docs/application/pipelines/chembl/00-index.md)**: Описание ETL-пайплайнов ChEMBL.
- **[Infrastructure](docs/infrastructure/00-index.md)**: Клиенты, конфигурация, логирование.
- **[Guides](docs/guides/00-running-pipelines.md)**: Руководства по запуску.

## Быстрый старт

```bash
# Установка
pip install -e .

# Запуск smoke-теста
bioetl run activity_chembl --profile development --dry-run
```

## Лицензия

MIT
