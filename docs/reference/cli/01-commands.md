# CLI Commands

Список доступных команд утилиты `bioetl`.

## `run`

Запуск ETL-пайплайна.

```bash
bioetl run [PIPELINE_NAME] [OPTIONS]
```

**Аргументы:**
- `PIPELINE_NAME`: Имя пайплайна (например, `activity_chembl`).

**Опции:**
- `--profile TEXT`: Профиль конфигурации (`development`, `production`). По умолчанию `default`.
- `--dry-run / --no-dry-run`: Запуск без записи результатов. По умолчанию `False`.
- `-o, --output PATH`: Путь к директории вывода.
- `--set KEY=VALUE`: Переопределение параметров конфига (можно указывать несколько раз).

## `validate-config`

Проверка валидности конфигурационного файла.

```bash
bioetl validate-config [CONFIG_PATH]
```

**Аргументы:**
- `CONFIG_PATH`: Путь к YAML-файлу конфигурации.

## `list-pipelines`

Вывод списка доступных пайплайнов.

```bash
bioetl list-pipelines
```

## `smoke-run`

Запуск быстрого дымового тестирования для указанного пайплайна (аналог `--profile development --dry-run`).

```bash
bioetl smoke-run [PIPELINE_NAME]
```

