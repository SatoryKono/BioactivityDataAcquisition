# Grok CLI для BioETL

> **Archived** 2026-08-04 (docs architecture audit cycle 3 / #7432).
> Obsolete: `scripts/grok_cli.py`, `scripts/grok_cli_advanced.py`, and the
> `pygrok` package are **not** present in the current repository. Do not follow
> the commands below. Prefer current logging/ops guides under `docs/05-operations/`.

## Обзор

Grok CLI установлен в проекте через библиотеку `pygrok` и предоставляет функциональность для парсинга структурированных логов и текстовых данных с использованием Grok паттернов.

## Установка

```bash
pip install pygrok
```

## Использование

### Базовый CLI

Простой скрипт для базового парсинга:

```bash
python scripts/grok_cli.py '<pattern>' '<text>'
```

Пример:

```bash
python scripts/grok_cli.py '%{IP:client} %{WORD:method} %{URIPATHPARAM:request}' '192.168.1.1 GET /api/data'
```

### Продвинутый CLI

Расширенный скрипт с предопределенными паттернами:

```bash
# Показать список предопределенных паттернов
python scripts/grok_cli_advanced.py --list-patterns

# Использовать предопределенный паттерн
python scripts/grok_cli_advanced.py bioetl_log '2024-01-15T10:30:00Z INFO bioetl.pipelines - Pipeline started'

# Использовать кастомный паттерн
python scripts/grok_cli_advanced.py '%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level}' '2024-01-15T10:30:00Z INFO'

# С пользовательскими паттернами
python scripts/grok_cli_advanced.py custom_pattern 'text' --custom-patterns patterns.json
```

## Предопределенные паттерны

- `bioetl_log`: Базовый формат логов BioETL
- `pipeline_start`: Запуск пайплайна
- `pipeline_complete`: Завершение пайплайна
- `http_request`: HTTP запросы
- `error`: Сообщения об ошибках

## Использование в Python коде

```python
from pygrok import Grok

# Базовое использование
log_line = '55.3.244.1 GET /index.html 15824 0.043'
pattern = '%{IP:client} %{WORD:method} %{URIPATHPARAM:request} %{NUMBER:bytes} %{NUMBER:duration}'

grok = Grok(pattern)
result = grok.match(log_line)
print(result)
# {'client': '55.3.244.1', 'method': 'GET', 'request': '/index.html', 'bytes': '15824', 'duration': '0.043'}
```

## Применение в BioETL

Grok CLI может использоваться для:

1. **Парсинга логов пайплайнов** - извлечение структурированных данных из логов
2. **Валидации форматов данных** - проверка соответствия данных ожидаемым паттернам
3. **Анализа ошибок** - структурирование сообщений об ошибках
4. **Тестирования трансформаций** - проверка выходных данных пайплайнов

## Интеграция с пайплайнами

Для интеграции с пайплайнами BioETL можно создать адаптер:

```python
from pygrok import Grok
from typing import Dict, Any

class GrokParser:
    """Адаптер для парсинга данных с использованием Grok паттернов."""
    
    def __init__(self, pattern: str, custom_patterns: Dict[str, str] = None):
        self.grok = Grok(pattern, custom_patterns=custom_patterns)
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Парсит текст и возвращает словарь с полями."""
        return self.grok.match(text)
    
    def parse_batch(self, texts: list) -> list:
        """Парсит список текстов."""
        return [self.parse(text) for text in texts]
```

## Ссылки

- [pygrok documentation](https://github.com/hangs13/pygrok)
- [Grok patterns reference](https://github.com/logstash-plugins/logstash-patterns-core/blob/main/patterns)