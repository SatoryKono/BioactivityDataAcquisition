______________________________________________________________________

Version: 0.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-07'

______________________________________________________________________

# D-05 Pipelines & Config Specification

Краткий guide по каноническому runtime-конфигу BioETL, валидациям и обязательным примерам.

## Основные ссылки

- `docs/03-guides/pipeline-configuration.md` — шаблон `configs/entities/{provider}/{entity}.yaml`, объяснение секций `pipeline/schema/quality/filters/contracts`, шаблон `config.yaml.tpl`.
- `docs/04-reference/templates/*` — шаблоны `config.yaml.tpl`, `factory.py.tpl`, `pipeline.py.tpl`, `provider-spec-template.md`, а также образцы `source_adapter`.
- `docs/03-guides/add-new-source.md` / `docs/03-guides/add-pipeline-existing-source.md` — пошаговые чеклисты: от provider config до transformer/registry/test.
- `rules` и CI: `docs/00-project/RULES.md`, `scripts/schema validate-configs`, архитектурные `tests/architecture`.

## Что должно быть в спецификации

1. **Три уровня конфигов** (base/provider/entity) существуют в `configs/` и задействуются одновременно: базовые дефолты, политики провайдера и канонические entity YAML.
2. **Entity config** всегда содержит секции `pipeline/schema/quality/filters/contracts` (включайте пустые `{}` вместо отсутствия).
3. **Pipeline block** оформляется по шаблону: `pipeline_name`, `provider/entity`, `description`, `loading_strategy`, `batch_size`, `sink` для Bronze/Silver/Gold, optional overrides (`extraction_params`, `dq_overrides`, `filter_rules`).
4. **Schema/quality/contracts** валидируются JSON Schema + Pydantic (`extra='forbid'`, `strict=True`), composite configs имеют отдельное JSON Schema.
5. **Provider config** (`configs/providers/{provider}.yaml`) описывает `source.provider_config`, `pagination`, `rate_limit`, `entities`, `quality`, `filters`, `circuit_breaker`, `health_check`.

## Артефакты, которые должны путешествовать в пайплайн-релизе

| Тип | Где хранится | Что описывает |
|---|---|---|
| Unified entity config | `configs/entities/{provider}/{entity}.yaml` | runtime YAML + schema/quality/filters/contracts |
| Provider config | `configs/providers/{provider}.yaml` | сетевые параметры, rate limits, health и список entities |
| Transformer | `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py` | бизнес-трансформация |
| Silver schema | `src/bioetl/domain/schemas/{provider}/{entity}.py` | Pandera-валидация |
| Gold contract | `src/bioetl/domain/contracts/gold/{provider}.py` | DataFrameModel, экспортирован в `contracts/__init__` |
| Registries | `transformer_factory.py`, `pipeline/registry.py`, `composition/providers/registration.py` | DI и runtime registration |
| Tests | unit + architecture, опционально integration/VCR |

## Проверки и CI-гейты

- `uv run python -m scripts.schema validate-configs --verbose`
- `python -c "from bioetl.infrastructure.config import load_pipeline_config; load_pipeline_config('{provider}_{entity}'); print('ok')"`
- `uv run python -m pytest tests/architecture/test_registry_contracts.py -q`
- `uv run python -m pytest tests/architecture/test_source_config_usage.py -q`
- `uv run python -m pytest tests/unit/application/pipelines/{provider}/ -q`
- при наличии API-доступа добавлять интеграционные тесты `tests/integration/ -k {provider}` или VCR репорты.

## Критерии завершения

- runtime YAML проходит JSON Schema + Pydantic + CI (forbid unknown keys, требуемые секции, запрет секретов).
- transformer и pipeline зарегистрированы (transformer factory + `PIPELINE_CONFIGS`).
- Silver и Gold схемы доступны и экспортированы.
- unit tests + architecture smoke проходят.
- `uv run python -m bioetl run --pipeline {provider}_{entity} --limit 10` выполняется без ошибок.
- документация (`provider-spec-template`, README провайдера, D-02 handbook) обновлена и ссылается на CI/health.

Обновляйте D-05 одновременно с изменениями в шаблонах/валидаторах (поддерживайте бифорт или мерж-обновление `docs/03-guides/pipeline-configuration.md`). 
