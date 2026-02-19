# Руководство по разработке BioETL

Это руководство содержит сведения, специфичные для проекта BioETL, и предназначено для опытных разработчиков.

## 1. Сборка и настройка (Build/Configuration)

Проект использует `uv` в качестве основного менеджера пакетов и `make` для автоматизации задач.

### Основные шаги:

1. **Установка зависимостей**:
   ```powershell
   # Рекомендуемый способ (автоматизированная настройка)
   ./dev_setup.sh
   
   # Альтернатива (через make)
   make install
   
   # Если make недоступен (Windows PowerShell)
   uv sync --extra dev --extra tracing
   ```
2. **Переменные окружения**:
   Создайте `.env` файл в корне проекта для хранения секретов (API ключи NCBI, ChEMBL и др.). Проект использует
   `pydantic-settings` для подгрузки конфигурации. Базовая логика конфига: `src/bioetl/domain/config.py`.

3. **Архитектура и Слои**:
   Соблюдение границ слоев (Hexagonal Architecture) критично:

- **Domain** (`src/bioetl/domain`): Чистая логика, порты (Protocols), агрегаты. **Запрещен I/O и импорт инфраструктуры
  **.
- **Application** (`src/bioetl/application`): Оркестрация, пайплайны.
- **Infrastructure** (`src/bioetl/infrastructure`): Адаптеры (HTTP, Delta Lake), реализация портов.
- **Composition** (`src/bioetl/composition`): Единственное место для сборки зависимостей (DI Root).
- **Interfaces** (`src/bioetl/interfaces`): CLI и входные точки.

## 2. Тестирование (Testing)

Целевое покрытие тестами — **≥85%** (проверяется в CI: `--cov-fail-under=85`).

### Запуск тестов:

- **Все тесты**: `make test` или `uv run pytest tests/`
- **Unit-тесты**: `make test-unit`
- **Интеграционные тесты**: `make test-integration` (используют `VCR.py`, кассеты в `tests/fixtures/vcr/`)
- **Архитектурные тесты**: `make arch-test` (проверяют импорты и границы слоев через `import-linter`)

### Добавление новых тестов:

1. Файлы тестов размещайте в поддиректориях `tests/unit/`, `tests/integration/` или `tests/architecture/`.
2. Все функции тестов должны иметь аннотации типов возвращаемого значения (`-> None`).
3. Используйте `from __future__ import annotations` для поддержки современных типов.

### Пример проверенного теста:

```python
from __future__ import annotations
import pytest

@pytest.mark.unit
def test_guidelines_example() -> None:
    """Пример теста бизнес-логики с использованием pytest marks."""
    result = 1 + 1
    assert result == 2

def test_data_structure() -> None:
    """Пример теста со сложной структурой данных и аннотациями."""
    data: dict[str, str | list[int]] = {"status": "success", "items": [1, 2, 3]}
    assert data["status"] == "success"
    assert len(data["items"]) == 3
```

## 3. Дополнительная информация по разработке

### Качество кода и инструменты:

- **Linter**: `ruff`. Команда: `make lint` или `uv run ruff check src/`.
- **Static Type Checking**: `mypy --strict`. Все публичные API и функции должны быть типизированы.
- **Logging**: Используйте `LoggerPort`. Не импортируйте `structlog` напрямую вне слоя инфраструктуры или композиции.
- **Dependency Injection**: Только через конструктор (`__init__`). Не создавайте экземпляры зависимостей внутри классов.

### Протокол верификации (Architectural Verification):

Перед внесением изменений в архитектуру или рефакторингом **ОБЯЗАТЕЛЬНО** проверьте текущее состояние кодом (grep/wc), а
не полагайтесь на документацию. См. `CLAUDE.md` для подробностей о протоколе двойной верификации.

### Работа на Windows:

Если `make` недоступен, используйте `uv run pytest`, `uv run ruff check`, `uv run mypy`.

## 4. Ресурсы для AI Агентов

Для эффективной работы с AI агентами (Claude, Gemini, JetBrains AI Assistant) используйте следующие ресурсы:

- **[AI_RULES.md](../AI_RULES.md)**: Единый источник правды по инвариантам проекта. Рекомендуется "скармливать" агенту в
  начале каждой сессии.
- **[.junie/prompts/](prompts/)**: Библиотека готовых промтов для типичных задач:
  - [Рефакторинг под Hexagonal Architecture](prompts/refactor_to_hexagonal.md)
  - [Генерация тестов по стандартам проекта](prompts/test_generation.md)
  - [Проектирование схем данных](prompts/schema_design.md)
  - [Аудит кода (Self-review)](prompts/self_review.md)

---
*Синхронизировано с внутренними правилами проекта BioETL.*
