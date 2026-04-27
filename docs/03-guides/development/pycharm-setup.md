# Настройка PyCharm для разработки BioETL

В репозитории поставляются готовые настройки для IDE PyCharm (в папке `.idea`), которые автоматизируют запуск тестов, проверку качества кода и навигацию по слоям архитектуры.

## 1. Интерпретатор (Python SDK)

Рекомендуется использовать Python 3.13. Для Windows настроен SDK, указывающий на `.venv-win`.
Если вы используете другую ОС или путь к виртуальному окружению отличается:

- Зайдите в **Settings** > **Project: BioactivityDataAcquisition** > **Python Interpreter**.
- Выберите интерпретатор из вашего `.venv` (созданного через `uv sync`).

## 2. Общие конфигурации запуска (Shared Run Configurations)

Доступны следующие группы конфигураций (кнопка в верхней панели или `Shift+F10`):

### Пайплайны (Pipelines)

- **BioETL: Run molecule (Limit 10)** — быстрый запуск пайплайна молекул.
- **BioETL: Run assay (Limit 10)** — запуск пайплайна анализов.
- **BioETL: Run target (Limit 10)** — запуск пайплайна мишеней.
- **BioETL: Run publication (Limit 10)** — запуск пайплайна публикаций.
- **BioETL: Run activity (Limit 10)** — запуск пайплайна активностей.
- **BioETL Run chembl_molecule** — полный запуск ChEMBL Molecule.

### Качество и Документация (QA & Docs)

- **Scripts: QA (Check)** — запуск `scripts.engineering.qa check` (линтеры, типы).
- **Scripts: Schema (Validate)** — проверка всех YAML конфигов.
- **Scripts: Docs (Check Links)** — проверка ссылок и спецификаций в документации.
- **Mypy Strict** — запуск MyPy в строгом режиме.
- **uv QA Check** — запуск полной проверки через uv.

### Тестирование (Testing)

- **Pytest All** — все тесты.
- **Pytest Unit** — только юниты.
- **Pytest Integration** — интеграционные тесты.
- **Pytest Architecture** — проверка границ слоев (Hexagonal Architecture).

## 3. Области видимости (Scopes)

Для удобства навигации по гексагональной архитектуре созданы Shared Scopes:

- **Domain** — `src/bioetl/domain/`
- **Application** — `src/bioetl/application/`
- **Infrastructure** — `src/bioetl/infrastructure/`
- **Interfaces** — `src/bioetl/interfaces/`
- **Composition** — `src/bioetl/composition/`

Используйте их в диалогах поиска (`Ctrl+Shift+F` > **Scope**) или при анализе зависимостей.

## 4. Инспекции и Code Style

- **Ruff**: Настроен как основной линтер и форматер (выполняется при сохранении).
- **MyPy**: Интегрирован через плагин.
- **Docstrings**: Включена проверка на отсутствие docstrings в публичных методах (Weak Warning).
- **Словарь**: В `.idea/dictionaries/project.xml` добавлены биологические и технические термины (ChEMBL, PubChem, Pandera, DeltaLake и др.), чтобы избежать ложных срабатываний спелл-чекера.

## 5. Полезные Live Templates (Рекомендации)

Для быстрого создания новых компонентов рекомендуется добавить следующие шаблоны:

- `bioport` -> `Protocol` для порта в Domain.
- `bioschema` -> `pa.DataFrameModel` для Pandera схемы.
- `bioadapter` -> Класс адаптера в Infrastructure.
