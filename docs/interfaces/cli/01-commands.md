# 01 Commands

## run
- Назначение: запуск одного или нескольких пайплайнов.
- Основные опции: `--pipeline <name>`, `--config <path>`, `--profile dev|prod`, `--output-dir <path>`, `--dry-run`.
- Пример: `bioetl run --pipeline chembl_activity --config configs/pipelines/chembl/activity.yaml --profile dev`.

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
