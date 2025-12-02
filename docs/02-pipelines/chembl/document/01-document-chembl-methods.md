# 01 Document ChEMBL Methods

## Описание

Документ описывает приватные методы `ChemblDocumentPipeline`, используемые для настройки обогащения и обработки данных документов.

## Внутренние методы

### `_resolve_mode(self, config: Mapping[str, Any]) -> str`

Определяет режим работы пайплайна (`chembl` или `all`).

**Параметры:**
- `config` — конфигурация пайплайна

**Возвращает:** режим работы ("chembl" или "all").

### `_resolve_fallback_policy(self, config: Mapping[str, Any]) -> str`

Читает политику fallback из конфига (`ordered`, `best_effort` или `strict`).

**Параметры:**
- `config` — конфигурация пайплайна

**Возвращает:** политику fallback ("ordered", "best_effort" или "strict").

### `_build_enrichment_chain(self) -> tuple[str, ...]`

Формирует цепочку источников обогащения (cache, Semantic Scholar, PubMed, Crossref) в зависимости от режима.

**Возвращает:** кортеж с именами источников обогащения в порядке применения.

### `_apply_enrichment_chain(self, df: pd.DataFrame) -> pd.DataFrame`

Проставляет метки о цепочке обогащения и политике fallback в DataFrame.

**Параметры:**
- `df` — DataFrame для обогащения

**Возвращает:** DataFrame с метками обогащения.

## Related Components

- **ChemblDocumentPipeline**: основной пайплайн для document (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)

