# 00 CLI Overview

The BioETL command-line interface (CLI) is the primary way to run pipelines, validate configurations, and integrate with automation tools such as CI.

This document provides a high-level overview of the CLI design and how it relates to configuration and project rules.

## Entry Points

The CLI is implemented using Typer and exposed through a static registry of commands.

Depending on your installation, you may invoke the CLI via a console script (for example `bioetl`) or by running the module directly (for example `python -m bioetl.cli`).

In the examples below, `bioetl` is used as a placeholder for whatever entry point is configured in your environment.

## Architecture

CLI состоит из трёх основных компонентов:

1. **cli_app.py** — инициализация приложения Typer, определение базовых команд и генерация команд для зарегистрированных пайплайнов
2. **cli_command.py** — создание Typer-команд для конкретных пайплайнов с обработкой конфигураций и исключений
3. **cli_registry.py** — централизованный реестр доступных пайплайнов для динамического создания команд

**Модули:**

- `src/bioetl/cli/cli_app.py` — главное приложение CLI
- `src/bioetl/cli/cli_command.py` — создание команд для пайплайнов
- `src/bioetl/cli/cli_registry.py` — реестр пайплайнов

## Design Principles

- **Explicit commands and flags**: Prefer explicit named options over ambiguous positional arguments
- **Deterministic behavior**: Identical inputs and configuration should lead to byte-identical outputs
- **Idempotent commands**: Running the same command twice with the same inputs should not produce conflicting or inconsistent artifacts
- **Clear exit codes**: Successful commands exit with code `0`. Validation or runtime errors result in non-zero exit codes that can be checked in CI

## Key Features

- **Динамическая регистрация пайплайнов**: автоматическое создание команд для всех зарегистрированных пайплайнов
- **Унифицированные опции**: общие параметры для выгрузки, валидации и конфигурации
- **Обработка ошибок**: корректные коды выхода и структурированные сообщения об ошибках
- **Профили конфигураций**: поддержка различных профилей конфигурации через CLI-переопределения
- **Групповой запуск**: команда для запуска всех пайплайнов определённого провайдера

## Relationship to IDE Commands

In the development environment, convenience commands may be exposed as IDE slash commands (for example `/run-activity-chembl` or `/run-chembl-all`).

These commands are thin wrappers around the same underlying CLI functionality described in this section and should follow the same contracts for flags, determinism, and exit codes.

## Logging and Observability

All CLI commands are expected to:

- Initialize a unified run context (for example `run_id`, `pipeline`, `stage`, `dataset`, `source`)
- Emit structured logs via UnifiedLogger instead of using `print` or raw logging calls

This ensures that pipeline runs are observable and can be audited in production and CI environments.

## Related Components

- **UnifiedLogger**: структурированное логирование (см. `docs/reference/infrastructure/logging/02-logging-and-configuration.md`)
- **FileConfigResolver**: резолвер конфигурации (см. `docs/reference/infrastructure/config/00-config-resolver.md`)
- **PipelineBase**: базовый класс пайплайнов, выполняемых через CLI
- **ConfigResolverABC**: разрешение конфигураций для пайплайнов
- **CLICommandABC**: интерфейс для плагинных команд CLI (см. `docs/reference/abc/02-cli-command-abc.md`)
