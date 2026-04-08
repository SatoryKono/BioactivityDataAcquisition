______________________________________________________________________

Version: 0.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-07'

______________________________________________________________________

# D-02 Provider Integration Handbook

Этот документ фиксирует актуальные требования, контрольные точки и ссылки на канонические руководства по включению нового провайдера и сущностей в BioETL. Актуальность проверяется одновременно с `docs/03-guides/add-new-source.md` и `docs/03-guides/add-pipeline-existing-source.md`.

## Резюме

- `configs/providers/{provider}.yaml` — единственный источник сетевых, таймаутных и политических настроек провайдера.
- `src/bioetl/infrastructure/adapters/{provider}/` содержит HTTP-клиент/адаптер, реализующий `DataSourcePort` и `HealthCheckPort`.
- `src/bioetl/composition/providers/registration.py` регистрирует провайдера через `ProviderRegistry`, а все трансформеры/конфигурации регистрируются через `transformer_factory` и `pipeline/registry.py`.
- `docs/03-guides/add-new-source.md` описывает полный путь «новый провайдер → первый pipeline», `docs/03-guides/add-pipeline-existing-source.md` подсказывает, как добавить следующую сущность к существующему провайдеру, `docs/03-guides/pipeline-configuration.md` описывает шаблоны конфигов и `docs/00-project/RULES.md` — требования по контрактам/health.

## Канонические источники

- `docs/03-guides/add-new-source.md` — основной чеклист по добавлению нового провайдера, включая шаблоны конфига, адаптер и регистрацию.
- `docs/03-guides/add-pipeline-existing-source.md` — чеклист по добавлению новой сущности/пайплайна для уже существующего провайдера.
- `docs/03-guides/pipeline-configuration.md` — шаблоны runtime YAML, объяснение секций `pipeline/schema/quality/filters/contracts` и валидаторы.
- `docs/04-reference/templates` — шаблоны `config.yaml.tpl`, `source_adapter.py.tpl`, `pipeline.py.tpl`, `factory.py.tpl` и `provider-spec-template.md`.
- `docs/00-project/RULES.md` — правила названий, DI, схем и требований к логированию/health/rate-limit.
- `docs/03-guides/dq-configuration.md` и `docs/03-guides/silver-schema-testing-guide.md` — требования к Pandera-схемам и проверке качества.

## Жизненный цикл провайдера

1. **Согласование Scope**: уточнить API, авторизацию и матрицу сущностей; выбрать первую сущность (обычно публичная публикация). Сравнить с `configs/providers/` и `configs/entities/` на предмет дубликатов.
2. **Provider source config**: применять шаблон из `configs/providers/{provider}.yaml`, прописать `source.provider_config`, `rate_limit`, `health_check`, `entities` и `quality`/`filters`. Секреты — только env vars согласно `docs/03-guides/add-new-source.md`.
3. **Инфраструктурный адаптер**: использовать `docs/04-reference/templates/source_adapter.py.tpl`, обеспечить поддержку `fetch` и `health_check`, пользоваться `UnifiedHTTPClient` и `BaseAuthConfig`. Раздел `client` должен быть инкапсулирован в `infrastructure` (без ссылок в application/domain).
4. **Composition registration**: обновить `src/bioetl/composition/providers/registration.py`, добавив creator и регистрируя `ProviderConfig`. Для кастомного lifecyle использовать `custom_creator=`; не менять динамическое поведение уже зарегистрированных провайдеров.
5. **Первый pipeline**: выполнить все шаги из `docs/03-guides/add-pipeline-existing-source.md`: `configs/entities/{provider}/{entity}.yaml`, transformer, Silver schema, Gold contract, регистрация фабрик, optional tests.
6. **Дополнительные сущности**: каждый новый entity поддерживает предыдущий цикл, но менее масштабный (фокус на config/transformer/schema/contract/registry). Все конфиги перекладываются через шаблон `docs/03-guides/pipeline-configuration.md`.
7. **Документирование**: обновить провайдерский README/handbook, `docs/04-reference/provider-spec-template.md` и `docs/00-project/index.md` (провайдер-список) с кратким summary и ссылками на CI/health.

## Контрольные валидации

- `uv run python -m scripts.schema validate-configs --verbose`
- `python -c "from bioetl.infrastructure.config import load_source_config, load_pipeline_config; load_source_config('{provider}'); load_pipeline_config('{provider}_{entity}'); print('ok')"`
- `uv run python -m pytest tests/architecture/test_registry_contracts.py -q`
- `uv run python -m pytest tests/architecture/test_source_config_usage.py -q`
- `uv run python -m pytest tests/unit/application/pipelines/{provider}/ -q`
- Добавлять интеграционные/VCR тесты `tests/integration/ -k {provider}` при наличии API access.

## Примеры артефактов

| Артефакт | Описание | Примерное расположение |
|---|---|---|
| Provider config | политики rate limit/backoff/pagination, entities list | `configs/providers/{provider}.yaml` |
| Infrastructure adapter | сеть и health | `src/bioetl/infrastructure/adapters/{provider}/client.py` |
| Transformer | бизнес-трансформация | `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py` |
| Silver schema | Pandera схему | `src/bioetl/domain/schemas/{provider}/{entity}.py` |
| Gold contract | DataFrameModel | `src/bioetl/domain/contracts/gold/{provider}.py` |
| Pipeline config | runtime YAML | `configs/entities/{provider}/{entity}.yaml` |
| Registration | DI/registry настройка | `src/bioetl/composition/providers/registration.py`, `transformer_factory.py`, `pipeline/registry.py` |

## Документация провайдера

- `docs/04-reference/provider-spec-template.md` — шаблон provider-spec, обязателен для каждого нового provider: описывать `auth`, `scope`, `rate_limits`, `entities`, `health`.
- Обновить `docs/03-guides/add-new-source.md` и `docs/03-guides/add-pipeline-existing-source.md` по мере изменений в пайплайнах.
- Указать место ответственного и дату ревью для каждого handbook.

## Критерии завершения

- провайдер и его сущности прошли все config/schema/contract/registry проверки;
- `uv run python -m bioetl run --pipeline {provider}_{entity} --limit 10` выполняется без ошибок;
- документация `docs/04-reference/provider-spec.md` и README провайдера описывает режимы загрузки и health checks.
- CI включает проверку вайтинга конфигов (`scripts.schema validate-configs`), архитектурные smoke и targeted unit/integration тесты.

Периодически сверять этот документ с `docs/03-guides/add-new-source.md` — при изменении порядка шагов обновлять `D-02` как карту ориентации.
