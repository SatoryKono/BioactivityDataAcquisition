# Аудит технического долга — src/bioetl (full, MODE=audit)

Дата: 2026-09-17. Язык: ru. Scope: src/bioetl. Режим: read-only (без патчей).

## Итог
- surface_score: 2 — основной долг контролируется, часть подавлений неформальна.
- Проверено по заданию: nosec B105/B405 (были «только grep, тела не открыты») — тела открыты, вердикт ниже.
- TODO/FIXME/HACK/XXX в src/bioetl поиском не найдены (пустая выдача).
- Бюджет долга/качества не повышался. .env не трогался. Коммитов нет.

## Резолюция B105 (hardcoded password — NOT_PROVEN как уязвимость)
Открыты тела:
- src/bioetl/application/pipelines/chembl/molecule_transformer.py:64-65,82 — ключи словарей `full_molformula`, `ro3_pass` (ChEMBL-названия полей), не пароли.
- src/bioetl/domain/composite/cross_validation.py:41 — `PASS = "pass"` (CrossValidationVerdict), не credential.
- src/bioetl/domain/types/dq_contracts.py:19 — `PASS = "pass"` (DQDisposition), не credential.
- src/bioetl/domain/value_objects/dq_report_enums.py:19,27 — `PASS = "pass"` (DQCheckStatus, DQReportStatus), не credential.
Вердикт: все 4 — ложноположительные срабатывания Bandit B105; `nosec B105` обоснован. Долг: шумные супрессии без централизованного exemption-реестра (P3).

## Резолюция B405 (xml.etree — NOT_PROVEN как уязвимость)
Открыты тела:
- src/bioetl/application/pipelines/pubmed/transformer.py:10,13,149 — `import xml.etree.ElementTree as ET  # nosec B405` только для типов/ParseError; реальный парсинг `defused_ET.fromstring(raw_xml)` (строка 149) с обработкой EntitiesForbidden.
- src/bioetl/infrastructure/adapters/pubmed/xml_processor.py:16,18,37 — аналогично: типы через ET, парсинг через `defused_ET.fromstring(xml_text)`.
- src/bioetl/application/pipelines/pubmed/extractors/base.py:12 — только `from xml.etree.ElementTree import Element` для аннотаций, парсинга нет.
- src/bioetl/application/pipelines/pubmed/xml_parser.py:11,29,34,59,64,67 — `ET.fromstring` только в docstring-примерах; продуктивного парсинга нет.
Поиск `fromstring` по src/bioetl подтверждает: продуктивные вызовы только `defused_ET.fromstring` (2 места выше).
Вердикт: XXE-уязвимости нет; `nosec B405` обоснован. Долг: ~14 супрессий B405 без реестра (P3); опция — алиас типа вместо импорта ET.

## Прочий долг (с файловыми доказательствами)
1. TD-01 (P2, code): концентрация `# type: ignore` (~70 совпадений поиском). Пример открыт: src/bioetl/application/services/ops/observability_backend_startup.py:122-147 — `hooks[...]` без типов, серия `type: ignore[operator]`. Blast radius: локальный; effort: S (ввести TypedDict/Protocol для hooks).
2. TD-02 (P2, architecture): `noqa: F403` star-реэкспорты в фасадах (`application/core/transformer_runtime/__init__.py`, `application/core/field_transforms/__init__.py`, `application/pipelines/openalex/extractors.py` и др.). Blast radius: средний (публичные API); effort: M (явные __all__ уже частично есть).
3. TD-03 (P3, code): широкие `except Exception` — открыты src/bioetl/application/services/execution/_pipeline_runner_support.py:98 (`_result_duration_seconds` → return None, безопасно) и src/bioetl/infrastructure/storage/silver/delta_write_execution.py:99-100 (thread boundary, с NOSONAR-обоснованием). Остальные ~11 мест не открыты — кандидаты, не доказанный долг.
4. TD-04 (P3, observability): 4 `NOSONAR` с обоснованием (aggregation_filters.py:9, cross_validation.py:69, delta_write_execution.py:99, workflow_foreign_key_reconciliation_quarantine_keys.py:27) — приемлемо, но без реестра.
5. TD-05 (P3, docs): docstring-примеры xml_parser используют незащищённый ET.fromstring — копипаст-риск; effort: XS (заменить на defusedxml в примерах).

## Top-20 / quick-wins vs strategic
- Quick wins (XS/S): TD-05 (docstring), консолидация B105/B405-супрессий в реестр, типизация hooks (TD-01 частично).
- Strategic (M): TD-02 (явные реэкспорты), типизация duck-type мест (TD-01 остаток).
- Зависимостный долг: не выявлен в scope (defusedxml уже используется).

## Remediation (без повышения бюджетов)
1. Завести реестр супрессий (nosec/NOSONAR/type-ignore) с owner и сроком пересмотра.
2. TD-05: поправить docstring в xml_parser.py.
3. TD-01: TypedDict для hooks в observability_backend_startup.py.
