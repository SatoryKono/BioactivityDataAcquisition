# 01 Commands

## run
- Назначение: запуск указанного пайплайна по имени.
- Синтаксис:
  ```bash
  bioetl run --pipeline-name <pipeline_name> [--config <path>] [--profile dev|prod] [--output-dir <path>] [--dry-run]
  ```
- Опции:
  - `--pipeline-name <pipeline_name>` (обязательно) — целевой пайплайн, запускаемый в текущем вызове.
  - `--config <path>` — путь к YAML-конфигурации пайплайна.
  - `--profile dev|prod` — профиль исполнения с предустановленными параметрами.
  - `--output-dir <path>` — каталог для выгрузки артефактов и отчётов.
  - `--dry-run` — проверка конфигураций и доступности источников без фактического выполнения шагов.
- Пример:
  ```bash
  bioetl run --pipeline-name chembl_activity --config configs/pipelines/chembl/activity.yaml --profile dev
  ```
- Примечание: команда принимает только одно значение `pipeline_name` за запуск; параллельный старт нескольких пайплайнов не поддерживается.

## validate-config
- Назначение: проверка YAML-конфигураций и профилей на полноту и корректность.
- Опции: `--config <path>`, `--profile <name>`.
- Пример: `bioetl validate-config --config configs/pipelines/chembl/activity.yaml --profile prod`.

## smoke-run
- Назначение: быстрый запуск с малыми лимитами для проверки доступности источников и схем.
- Опции: `--pipeline <name>`, `--config <path>`, `--limit <n>`.
- Пример: `bioetl smoke-run --pipeline chembl_assay --config configs/pipelines/chembl/assay.yaml --limit 100`.

## Дополнительные команды
Проект допускает регистрацию пользовательских команд (например, `list-pipelines`, `dump-schema`) через `CLICommandABC`. За подробностями см. `docs/guides/00-running-pipelines.md`.
