# Performance Optimizations

## 1. Ruff: параллельная обработка и кэширование

```toml
# pyproject.toml или ruff.toml
[tool.ruff]
# Увеличить количество воркеров для параллельной обработки
jobs = -1  # Использовать все доступные ядра

[tool.ruff.lint]
# Отключить медленные правила в dev-режиме
ignore = ["E501"]  # Длина строки - проверять только в CI

# Кэширование результатов
cache-dir = ".ruff-cache"
```

## 2. Mypy: инкрементальная проверка типов

```toml
# pyproject.toml
[tool.mypy]
# Включить инкрементальную проверку
incremental = true
cache_dir = ".mypy_cache"

# Исключить медленные модули из строгой проверки в dev
[[tool.mypy.overrides]]
module = ["tests.*", "scripts.*"]
strict = false
```

## 3. Pytest: параллельный запуск тестов

```toml
# pyproject.toml или pytest.ini
[tool.pytest.ini_options]
# Параллельный запуск тестов
addopts = "-n auto --dist worksteal"
# Кэширование результатов
cache_dir = ".pytest_cache"
# Быстрый выход при первой ошибке в dev
# addopts = "-n auto -x --ff"  # для локальной разработки
```

## 4. Pre-commit: оптимизация хуков

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        # Только изменённые файлы
        files: ^
      - id: ruff-format
        files: ^
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        # Только изменённые файлы
        files: ^
        additional_dependencies: [types-all]
        args: [--no-incremental]  # Быстрая проверка только изменений
```

## 5. Pandera: отключение валидации в dev

```python
# configs/dev.yaml или через переменные окружения
pandera:
  validation_enabled: false  # В dev-режиме для ускорения
  # Или использовать lazy validation
  lazy: true
```

## 6. Кэширование HTTP-запросов

```python
# src/bioetl/clients/base/config.py
class APIClientConfig:
    # Кэш для повторяющихся запросов в dev
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 час
    cache_dir: Path = Path(".api-cache")
```

## 7. Оптимизация импортов

```python
# Использовать lazy imports для тяжёлых модулей
# src/bioetl/__init__.py
def __getattr__(name: str):
    if name == "heavy_module":
        import heavy_module
        return heavy_module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## 8. Настройки IDE: исключения из индексации

```json
// .vscode/settings.json или .idea/
{
  "files.exclude": {
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/.ruff-cache": true,
    "**/__pycache__": true,
    "**/.api-cache": true,
    "**/dist": true,
    "**/build": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/.git": true,
    "**/venv": true
  }
}
```

## 9. Переменные окружения для быстрого переключения режимов

```bash
# .env.development
BIOETL_FAST_MODE=true
BIOETL_SKIP_VALIDATION=true
BIOETL_PARALLEL_WORKERS=8
BIOETL_CACHE_ENABLED=true

# .env.production
BIOETL_FAST_MODE=false
BIOETL_SKIP_VALIDATION=false
BIOETL_PARALLEL_WORKERS=4
BIOETL_CACHE_ENABLED=true
```

## 10. Оптимизация CI/CD: кэширование зависимостей

```yaml
# .github/workflows/ci.yml или аналогичный
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      .venv
      .pytest_cache
      .mypy_cache
      .ruff-cache
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements*.txt', '**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-deps-
```

## Дополнительные рекомендации

### Быстрый запуск тестов
```bash
# Запуск только быстрых unit-тестов
pytest -m "not integration and not slow" -n auto

# Запуск только изменённых тестов (с pytest-watch)
ptw --runner "pytest -n auto"
```

### Локальное кэширование данных
```python
# Использовать локальный кэш для больших датасетов
CACHE_DIR = Path(".data-cache")
CACHE_TTL = 86400  # 24 часа
```

### Оптимизация памяти
```python
# Использовать streaming для больших файлов
import pandas as pd
chunk_size = 10000
for chunk in pd.read_csv(large_file, chunksize=chunk_size):
    process_chunk(chunk)
```


