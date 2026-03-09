#!/usr/bin/env python3
"""Create Data Governance v2 GitHub issues.

Usage:
    GH_TOKEN=<your-github-token> python scripts/create-data-governance-issues.py

Or:
    python scripts/create-data-governance-issues.py --token <your-github-token>

Requires: requests (pip install requests)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPO = "SatoryKono/BioactivityDataAcquisition"
API_BASE = f"https://api.github.com/repos/{REPO}"


def api_request(
    method: str,
    path: str,
    token: str,
    data: dict | None = None,
) -> dict:
    """Make a GitHub API request."""
    url = f"{API_BASE}/{path}" if not path.startswith("https://") else path
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  API error {e.code}: {error_body}", file=sys.stderr)
        raise


def ensure_labels(token: str, labels: list[dict[str, str]]) -> None:
    """Create labels if they don't exist."""
    for label in labels:
        try:
            api_request("POST", "labels", token, label)
            print(f"  Created label: {label['name']}")
        except HTTPError as e:
            if e.code == 422:  # Already exists
                print(f"  Label exists: {label['name']}")
            else:
                raise


def ensure_milestone(token: str, title: str, description: str) -> int:
    """Create milestone if it doesn't exist, return milestone number."""
    # Check existing milestones
    try:
        milestones = api_request("GET", "milestones?state=open&per_page=100", token)
        for ms in milestones:
            if ms["title"] == title:
                print(f"  Milestone exists: {title} (#{ms['number']})")
                return ms["number"]
    except HTTPError:
        pass

    result = api_request("POST", "milestones", token, {
        "title": title,
        "description": description,
    })
    print(f"  Created milestone: {title} (#{result['number']})")
    return result["number"]


ISSUE_1_BODY = r"""## Problem

Отсутствует формализованный механизм отслеживания происхождения данных от Gold-слоя до исходного API-ответа. Исследователь, использующий запись из Gold-таблицы в публикации, не может программно восстановить полную цепочку трансформаций и подтвердить, из какого API-вызова, в какой момент и через какие этапы обработки запись получена. Это критический пробел для воспроизводимости научных исследований — рецензенты и регуляторы всё чаще требуют полную провенанс-информацию.

При обнаружении ошибки в Gold-данных невозможно быстро выполнить root cause analysis: неясно, была ли ошибка в исходных данных провайдера, возникла при трансформации Bronze→Silver / Silver→Gold, или является артефактом конкретной версии pipeline.

В контексте композитных пайплайнов проблема усугубляется: один API-ответ может порождать записи в нескольких Silver/Gold-таблицах через ветвление DAG, и lineage превращается в граф, а не линейную цепочку.

## Proposed Solution

### 1. Lineage ID propagation
Сквозной `lineage_id` (UUID v4) генерируется при ingestion в Bronze и пропагируется через все трансформации. В Bronze `lineage_id` привязан к API request/response (endpoint URL, parameters, HTTP status, timestamp). В композитном пайплайне каждая стадия передаёт `lineage_id` как first-class column.

### 2. Delta Lake metadata enrichment
`userMetadata` в Delta commit log обогащается на каждой стадии: source table, transformation name, pipeline version (git SHA), input/output row counts, schema version. Автоматически через wrapper над Delta write operations.

### 3. Lineage graph store
Delta-таблица `lineage_graph`: `source_entity`, `target_entity`, `transformation`, `pipeline_version`, `run_id`, `timestamp`, `row_count_in`, `row_count_out`. Строится post-factum из Delta transaction logs scheduled job-ом (не замедляет основной pipeline). Поддерживает запросы: «для данной Gold-записи покажи все upstream-зависимости до Raw».

### 4. Python API
Функция `trace_lineage(gold_table, record_id) -> LineageChain` возвращает структурированную цепочку. Для визуализации — интеграция с DataHub/OpenLineage или минимальный UI.

### 5. Immutable Raw storage
Оригинальные API-ответы хранятся с HTTP-заголовками и метаданными запроса, retention ≥ 2 года. Данные старше 6 мес. — на S3 Glacier/IA.

## Integration with Composite Pipelines

Lineage аккумулируется как побочный эффект каждой стадии pipeline:

```python
@asset
def silver_compounds(context, bronze_compounds):
    result = transform(bronze_compounds)
    result["lineage_id"] = bronze_compounds["lineage_id"]  # propagate

    context.delta_write(result, user_metadata={
        "source": "bronze_compounds",
        "transform": "silver_compounds",
        "git_sha": GIT_SHA,
        "pipeline_run_id": context.run_id,
    })
```

При ветвлении (один Bronze → несколько Silver) lineage graph автоматически отражает DAG-структуру pipeline.

## Acceptance Criteria

- [ ] `lineage_id` генерируется при ingestion и пропагируется через Bronze → Silver → Gold
- [ ] Delta commit logs обогащены lineage-метаданными (source, transformation, git SHA)
- [ ] Создана и заполняется таблица `lineage_graph`
- [ ] Реализована и покрыта тестами функция `trace_lineage()`
- [ ] Raw API-ответы хранятся immutably с retention ≥ 2 года
- [ ] Валидация: для 100% записей Gold lineage восстанавливается до Raw
- [ ] Совместимость со стандартом OpenLineage
- [ ] Документация с архитектурной диаграммой lineage flow
"""

ISSUE_2_BODY = r"""## Problem

ADR-036 определяет политику версионирования Gold-контрактов, но проверка обратной совместимости при изменении схемы выполняется вручную и не интегрирована в CI/CD. Изменения Gold-схемы (добавление обязательного поля, переименование колонки, смена типа) ломают downstream consumers — notebooks, dashboards, scheduled reports, API-эндпоинты.

**Типичный инцидент:** разработчик меняет `confidence_score` с `DOUBLE` на `DECIMAL(10,4)`. Проходит ревью, деплоится, через часы ломается Spark-job аналитиков. Обнаруживается только при ручном запуске notebook. Время реагирования — часы до дней.

В контексте композитных пайплайнов проблема каскадирует: изменение схемы в одной ветке DAG может затронуть consumers, которые зависят от downstream-таблиц через несколько уровней трансформаций.

## Proposed Solution

### 1. Schema Registry
Delta-таблица `schema_registry`: `table_name`, `version`, `schema_json`, `timestamp`, `author`, `change_type` (`BACKWARD_COMPATIBLE` / `BREAKING`), `migration_notes`. Новая версия регистрируется автоматически при изменении Gold-схемы.

### 2. CI compatibility checks
При каждом PR, затрагивающем Gold-схему, автоматическое сравнение с production-версией. Классификация:

| Изменение | Классификация |
|-----------|---------------|
| Добавление nullable колонки | Compatible |
| Удаление колонки | Breaking |
| INT → BIGINT (расширение) | Compatible |
| DOUBLE → INT (сужение) | Breaking |
| Переименование колонки | Breaking |
| Изменение nullable → NOT NULL | Breaking |

Breaking changes блокируют merge без override от data steward.

### 3. Consumer registry & notification
Таблица `consumer_registry` — каждый notebook/dashboard/сервис регистрирует зависимость от Gold-таблиц и колонок. При breaking change в CI определяется список затронутых consumers, владельцы получают: GitHub mention в PR, Slack notification, описание изменения и рекомендации по миграции.

### 4. Deprecation workflow
Breaking changes требуют deprecation period (по умолчанию 4 недели). Старая и новая колонка сосуществуют, deprecated-поля помечены в metadata и продолжают заполняться. Warning при обращении. Удаление — только после подтверждения миграции всех consumers через registry.

### 5. Schema diff в PR
Автоматический human-readable комментарий в PR: added/removed/modified columns, классификация совместимости, затронутые consumers, required actions.

## Integration with Composite Pipelines

Schema check работает на двух уровнях:

**CI/CD (pre-deploy):** diff новой схемы vs production → блок или pass.

**Runtime (defensive assertion):** в каждой стадии pipeline — защита от drift, который CI не поймал (например, upstream провайдер изменил типы):

```python
@asset
def gold_table(context, silver_data):
    expected = load_from_registry("gold_compounds", version="current")
    result = transform_to_gold(silver_data)

    if not schema_compatible(result.schema, expected):
        raise SchemaBreakingChange(diff(result.schema, expected))
    return result
```

Через lineage graph (Issue #1) schema change автоматически показывает полный blast radius по DAG пайплайна.

## Acceptance Criteria

- [ ] `schema_registry` создан и заполнен для всех существующих Gold-таблиц
- [ ] CI pipeline включает автоматическую проверку backward compatibility
- [ ] Breaking changes блокируют merge без override от data steward
- [ ] `consumer_registry` реализован с API для регистрации зависимостей
- [ ] Notification pipeline нотифицирует владельцев затронутых consumers
- [ ] Deprecation workflow документирован и интегрирован
- [ ] Schema diff автоматически публикуется как комментарий к PR
- [ ] Интеграционные тесты покрывают все типы schema changes
- [ ] ADR-036 обновлён с описанием автоматизированного процесса
"""


ISSUES = [
    {
        "title": "Data Lineage Graph — трассируемость Gold-записей до исходного API-ответа",
        "body": ISSUE_1_BODY.strip(),
        "labels": ["data-lineage", "reproducibility", "priority:critical"],
    },
    {
        "title": "Schema Evolution Policy — автоматизация backward-compatibility checks для Gold-схемы",
        "body": ISSUE_2_BODY.strip(),
        "labels": ["schema-evolution", "breaking-changes", "developer-experience", "priority:high"],
    },
]

LABELS_TO_CREATE = [
    {"name": "data-lineage", "color": "0E8A16", "description": "Data provenance and lineage tracking"},
    {"name": "reproducibility", "color": "D93F0B", "description": "Scientific reproducibility"},
    {"name": "schema-evolution", "color": "1D76DB", "description": "Schema versioning and evolution"},
    {"name": "breaking-changes", "color": "B60205", "description": "Breaking changes management"},
    {"name": "developer-experience", "color": "FBCA04", "description": "Developer experience improvements"},
]

MILESTONE_TITLE = "Data Governance v2"
MILESTONE_DESC = "Data governance features including lineage, schema evolution, and compliance"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Data Governance v2 GitHub issues")
    parser.add_argument("--token", help="GitHub token (or set GH_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Print issues without creating")
    args = parser.parse_args()

    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    if args.dry_run:
        for i, issue in enumerate(ISSUES, 1):
            print(f"\n{'='*60}")
            print(f"Issue {i}: {issue['title']}")
            print(f"Labels: {', '.join(issue['labels'])}")
            print(f"Milestone: {MILESTONE_TITLE}")
            print(f"{'='*60}")
            print(issue["body"][:200] + "...")
        print(f"\nDry run complete. {len(ISSUES)} issues would be created.")
        return

    if not token:
        print("Error: No GitHub token provided.", file=sys.stderr)
        print("Set GH_TOKEN environment variable or use --token flag.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating issues in {REPO}...")

    # 1. Ensure labels exist
    print("\n[1/3] Creating labels...")
    ensure_labels(token, LABELS_TO_CREATE)

    # 2. Ensure milestone exists
    print("\n[2/3] Creating milestone...")
    milestone_number = ensure_milestone(token, MILESTONE_TITLE, MILESTONE_DESC)

    # 3. Create issues
    print("\n[3/3] Creating issues...")
    created_urls = []
    for i, issue in enumerate(ISSUES, 1):
        print(f"\n  Creating issue {i}/{len(ISSUES)}: {issue['title'][:60]}...")
        result = api_request("POST", "issues", token, {
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue["labels"],
            "milestone": milestone_number,
        })
        url = result["html_url"]
        created_urls.append(url)
        print(f"  Created: {url}")

    print(f"\n{'='*60}")
    print(f"Successfully created {len(created_urls)} issues:")
    for url in created_urls:
        print(f"  {url}")


if __name__ == "__main__":
    main()
