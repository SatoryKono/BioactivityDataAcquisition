# Запуск тестов

## Устранение проблем

### Ошибка импорта numpy из исходников

Если вы видите ошибку:
```
ImportError: Error importing numpy: you should not try to import numpy from its source directory
```

Это означает, что в site-packages находится исходное дерево numpy вместо установленного пакета.

**Быстрое исправление:**
```bash
python scripts/fix_numpy_import.py
```

**Или вручную:**
1. Очистить PYTHONPATH:
   ```powershell
   $env:PYTHONPATH = $null
   ```
2. Переустановить numpy:
   ```bash
   pip uninstall numpy
   pip install numpy
   ```

## Быстрый старт

```bash
# Unit-тесты (быстрые, без сети)
npm test
# или
python -m pytest -m unit

# Все тесты с покрытием
npm run test:coverage
# или
python -m pytest --cov=src/bioetl --cov-report=term-missing --cov-fail-under=85
```

## Категории тестов

### Unit-тесты
Быстрые изолированные тесты без сетевых вызовов и IO.

```bash
npm run test:unit
# или
python -m pytest -m unit --ignore=tests/integration --ignore=tests/golden
```

### Интеграционные тесты
Тесты с реальными зависимостями (IO, сеть).

```bash
npm run test:integration
# или
python -m pytest -m integration tests/integration
```

### Golden-тесты
Тесты на соответствие эталонным артефактам.

```bash
npm run test:golden
# или
python -m pytest -m golden tests/golden
```

### Все тесты

```bash
npm run test:all
# или
python -m pytest tests/
```

## Покрытие кода

Минимальное покрытие: **85%** для `src/bioetl`.

```bash
# С текстовым отчётом
npm run test:coverage

# С HTML-отчётом
python -m pytest --cov=src/bioetl --cov-report=html --cov-fail-under=85
# Отчёт будет в htmlcov/index.html
```

## Скрипты

### Python-скрипт

```bash
# Unit-тесты
python scripts/run_tests.py unit

# С покрытием
python scripts/run_tests.py coverage --html

# Подробный вывод
python scripts/run_tests.py unit --verbose
```

### Bash-скрипт (Unix/Linux/Mac)

```bash
chmod +x scripts/run_tests.sh

./scripts/run_tests.sh unit
./scripts/run_tests.sh coverage
```

## NPM-скрипты

Все команды доступны через `npm run`:

- `npm test` / `npm run test:unit` - unit-тесты
- `npm run test:integration` - интеграционные тесты
- `npm run test:golden` - golden-тесты
- `npm run test:all` - все тесты
- `npm run test:coverage` - все тесты с покрытием
- `npm run test:verbose` - unit-тесты с подробным выводом

## Маркеры pytest

Доступные маркеры для фильтрации:

- `@pytest.mark.unit` - unit-тесты
- `@pytest.mark.integration` - интеграционные тесты
- `@pytest.mark.golden` - golden-тесты
- `@pytest.mark.determinism` - тесты детерминизма
- `@pytest.mark.property` - property-based тесты (Hypothesis)
- `@pytest.mark.schema` - тесты схем
- `@pytest.mark.qc` - тесты контроля качества
- `@pytest.mark.slow` - медленные тесты
- `@pytest.mark.network` - тесты с сетью
- `@pytest.mark.api` - тесты API-клиентов
- `@pytest.mark.benchmark` - бенчмарки

Пример использования:

```bash
# Только медленные тесты
pytest -m slow

# Исключить медленные тесты
pytest -m "not slow"

# Комбинация маркеров
pytest -m "unit and not slow"
```

## Конфигурация

Основная конфигурация pytest находится в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = ["-ra", "-q", "--strict-markers", "--strict-config", "--tb=short"]
```

Конфигурация coverage:

```toml
[tool.coverage.report]
fail_under = 85
```

## CI/CD

В CI запускаются все тесты с проверкой покрытия:

```bash
pytest --cov=src/bioetl --cov-report=xml --cov-fail-under=85
```

CI блокирует merge при покрытии < 85%.

