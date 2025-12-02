# 01 Configuration

## Структура YAML
- `configs/pipelines/<provider>/<entity>.yaml` — параметры пайплайна (пагинация, лимиты, детерминизм, qc, output_dir).
- Секции: `pagination`, `client` (базовый URL, таймауты, лимиты), `determinism` (column_order, сортировка), `qc`, `sources`/`targets`.

## Профили и extends
- Базовый файл может содержать блоки `profiles: {base, dev, prod}` с наследованием.
- dev расширяет base уменьшенными лимитами и включённым кэшем; prod усиливает ретраи и строгие политики.
- Поддерживается `extends` для переиспользования общих настроек.

## Пример
```yaml
profiles:
  base:
    pagination:
      page_size: 1000
    client:
      base_url: https://www.ebi.ac.uk/chembl/api/data
      rate_limit_rps: 5
    determinism:
      column_order: activity
    qc:
      enable: true
  dev:
    extends: base
    pagination:
      max_pages: 2
  prod:
    extends: base
    client:
      rate_limit_rps: 2
```

## Использование в пайплайнах
ConfigResolver читает YAML, применяет профиль и подставляет секреты из EnvSecretProvider. Пайплайн получает готовые параметры для клиента, валидаторов и вывода. Подробнее — `docs/infrastructure/config/00-index.md`.
