"""Pipeline-specific human projection facts built from canonical configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

JsonObject = dict[str, Any]


def _mapping(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _compact(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return ", ".join(map(str, value))
    if isinstance(value, dict):
        operator = value.get("operator")
        values = value.get("values")
        if operator and values is not None:
            return f"{operator} ({_compact(values)})"
        return ", ".join(f"{key}={_compact(item)}" for key, item in sorted(value.items()))
    return str(value)


def _provider_config(configs_root: Path, provider: str) -> JsonObject:
    path = configs_root / "providers" / f"{provider}.yaml"
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _mapping(payload)


def _field_groups(schema: JsonObject) -> list[JsonObject]:
    groups = []
    for raw in _list(schema.get("column_groups")):
        group = _mapping(raw)
        fields = [str(item) for item in _list(group.get("fields"))]
        if fields:
            groups.append(
                {
                    "name": str(group.get("name") or "unnamed"),
                    "fields": fields,
                    "field_count": len(fields),
                }
            )
    return groups


def _filters(payload: JsonObject) -> list[JsonObject]:
    configured = _mapping(payload.get("filters"))
    rows: list[JsonObject] = []
    for name, value in sorted(_mapping(configured.get("extraction_params")).items()):
        rows.append(
            {
                "name": str(name),
                "source": "config",
                "required": False,
                "description": _compact(value),
            }
        )
    input_filter = _mapping(configured.get("input_filter"))
    if input_filter:
        rows.append(
            {
                "name": str(input_filter.get("filter_field") or "operator_filter"),
                "source": "cli",
                "required": bool(input_filter.get("enabled")),
                "description": (
                    f"IDs from {input_filter.get('source_path')} column "
                    f"{input_filter.get('column_name')}; CLI may override the input CSV"
                ),
            }
        )
    return rows


def build_ordinary_projection(
    payload: JsonObject,
    *,
    configs_root: Path,
    provider: str,
    entity: str,
) -> JsonObject:
    """Build summary/extraction facts without duplicating runtime business logic."""
    pipeline = _mapping(payload.get("pipeline"))
    schema = _mapping(payload.get("schema"))
    quality = _mapping(payload.get("quality"))
    configured_filters = _mapping(payload.get("filters"))
    provider_payload = _provider_config(configs_root, provider)
    provider_source = _mapping(provider_payload.get("source"))
    provider_runtime = _mapping(provider_source.get("provider_config"))
    groups = _field_groups(schema)
    filters = _filters(payload)
    business_fields = next(
        (item["fields"] for item in groups if item["name"] == "business"),
        [],
    )
    selected_fields = [
        {
            "name": field,
            "source_object": entity,
            "target_group": "business",
            "required": field in _list(
                _mapping(configured_filters.get("silver_filters")).get(
                    "required_fields"
                )
            ),
        }
        for field in business_fields
    ]
    source_profile = _mapping(configured_filters.get("source_profile"))
    source_resource = str(
        source_profile.get("profile_id")
        or pipeline.get("source", {}).get("resource")
        if isinstance(pipeline.get("source"), dict)
        else ""
    )
    if not source_resource:
        source_resource = f"{provider}:{entity}"
    base_url = provider_runtime.get("base_url")
    source_kind = (
        "derived"
        if provider == "chembl"
        and entity
        in {
            "assay_parameters",
            "publication_similarity",
            "publication_term",
            "subcellular_fraction",
            "target_protein_classification",
        }
        else "http_api"
    )
    filter_summary = (
        "; ".join(f"{row['name']}={row['description']}" for row in filters)
        if filters
        else "без статических request-фильтров; scope задаётся effective config/CLI"
    )
    required_silver = [
        str(item)
        for item in _list(
            _mapping(configured_filters.get("silver_filters")).get("required_fields")
        )
    ]
    gold_filters = _mapping(configured_filters.get("gold_filters"))
    invalid_policy = str(
        quality.get("invalid_record_policy")
        or payload.get("invalid_record_policy")
        or "quarantine"
    )
    description = str(
        pipeline.get("description")
        or f"Extract {entity} records from the {provider} provider"
    )
    field_sample = business_fields[:8]
    sentences = [
        (
            f"{description.rstrip('.')}. Источник — `{source_resource}`"
            + (f" на `{base_url}`" if base_url else "")
            + f"; применяемые extraction/input filters: {filter_summary}."
        ),
        (
            "В business-проекцию входят "
            + ", ".join(f"`{field}`" for field in field_sample)
            + (
                f" и ещё {len(business_fields) - len(field_sample)} полей."
                if len(business_fields) > len(field_sample)
                else "."
            )
        ),
        (
            f"Silver использует профиль `{provider}.{entity}` и проверяет обязательные "
            f"поля {', '.join(f'`{field}`' for field in required_silver[:6]) or 'из effective DQ contract'}; "
            f"невалидные записи направляются в `{invalid_policy}`."
        ),
        (
            f"Перед Gold применяется строгий Pandera-контракт `{provider}.{entity}`; "
            f"Gold filters/constraints заданы в entity config"
            + (f" ({len(gold_filters)} групп правил)" if gold_filters else "")
            + "."
        ),
    ]
    return {
        "summary": {
            "sentences": sentences,
            "source_description": sentences[0],
            "query_filter_summary": filter_summary,
            "field_selection_summary": sentences[1],
            "silver_processing_summary": sentences[2],
            "validation_summary": sentences[3],
            "excluded_data_summary": f"invalid_record_policy={invalid_policy}",
        },
        "extraction": {
            "source_kind": source_kind,
            "source_resource": source_resource,
            "method": "GET" if source_kind == "http_api" else None,
            "endpoint_template": base_url,
            "source_tables": [],
            "source_collections": [entity],
            "filters": filters,
            "selected_fields": selected_fields,
            "field_groups": groups,
        },
        "normalization_profile": f"{provider}.{entity}",
    }


def operator_commands(pipeline_id: str, *, composite: bool = False) -> list[JsonObject]:
    """Return commands whose syntax is owned by the current Click CLI."""
    if composite:
        entity = pipeline_id.removeprefix("composite_")
        launch = f"bioetl run-composite --composite {entity}"
    else:
        launch = f"bioetl run --pipeline {pipeline_id}"
    return [
        {
            "task": "Запуск",
            "command": launch,
            "result": "Запускает pipeline с effective config.",
            "source_ref": (
                "src/bioetl/interfaces/cli/commands/run_composite.py"
                if composite
                else "src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py"
            ),
        },
        {
            "task": "Ограниченный запуск",
            "command": f"{launch} --limit 100",
            "result": "Ограничивает число обрабатываемых записей.",
            "source_ref": "src/bioetl/interfaces/cli/commands/domains/shared/click_options.py",
        },
        {
            "task": "Quarantine",
            "command": f"bioetl quarantine inspect --pipeline {pipeline_id} --limit 100",
            "result": "Показывает quarantined и Silver-filter records; доступны --error-code и --run-id.",
            "source_ref": "src/bioetl/interfaces/cli/commands/quarantine.py",
        },
        {
            "task": "Статистика исключений",
            "command": f"bioetl quarantine stats --pipeline {pipeline_id} --group-by reason-code",
            "result": "Группирует исключения; Gold/cross-validation причины видны только если runtime их публикует.",
            "source_ref": "src/bioetl/interfaces/cli/commands/quarantine.py",
        },
        {
            "task": "Checkpoint",
            "command": f"bioetl checkpoint inspect --pipeline {pipeline_id}",
            "result": "Показывает checkpoint и связанные audit/manifest anchors.",
            "source_ref": "src/bioetl/interfaces/cli/commands/checkpoint.py",
        },
        {
            "task": "Manifest",
            "command": "bioetl run-manifest show <run-id-or-manifest-id>",
            "result": "Показывает immutable manifest и ledger evidence запуска.",
            "source_ref": "src/bioetl/interfaces/cli/commands/run_manifest.py",
        },
    ]


def ordinary_mermaid(facts: JsonObject) -> str:
    """Render one bounded, deterministic pipeline data-flow diagram."""
    extraction = _mapping(facts.get("extraction"))
    silver = _mapping(facts.get("silver"))
    gold = _mapping(facts.get("gold"))
    identity = _mapping(facts.get("identity"))
    source = str(extraction.get("source_resource") or identity["pipeline_id"])
    profile = str(silver.get("normalization_profile") or identity["pipeline_id"])
    contract = str(gold.get("contract_ref") or identity["pipeline_id"])
    write = _mapping(gold.get("write")).get("mode") or "configured"
    return "\n".join(
        [
            "flowchart LR",
            f'    Source["{source}"]',
            '    Filters["Effective request/input filters"]',
            '    Bronze["Bronze append-only snapshot"]',
            f'    Silver["Silver profile: {profile} + DQ"]',
            '    Quarantine["Quarantine / exclusion evidence"]',
            f'    Gold["Gold: {contract} ({write})"]',
            "    Source --> Filters --> Bronze --> Silver",
            "    Silver -->|valid| Gold",
            "    Silver -->|invalid| Quarantine",
        ]
    )


def composite_mermaid(facts: JsonObject) -> str:
    """Render composite topology from its canonical config projection."""
    composite = _mapping(facts.get("composite"))
    seed = _mapping(composite.get("seed"))
    lines = [
        "flowchart LR",
        f'    Seed["Seed: {seed.get("pipeline", "unknown")}"]',
    ]
    previous = "Seed"
    for index, item in enumerate(
        [*_list(composite.get("dependencies")), *_list(composite.get("enrichers"))],
        start=1,
    ):
        row = _mapping(item)
        node = f"Input{index}"
        keys = ", ".join(map(str, _list(row.get("join_keys")))) or "configured keys"
        lines.append(f'    {node}["{row.get("pipeline", "input")} · {keys}"]')
        lines.append(f"    {node} --> Merge")
    merge = _mapping(composite.get("merge"))
    cross = _mapping(composite.get("cross_validation"))
    lines.extend(
        [
            f'    Merge["Merge: {merge.get("strategy", "configured")} / {merge.get("conflict_resolution", "configured")}"]',
            f'    Validate["Cross-validation: {cross.get("enabled", False)}"]',
            '    Excluded["Quarantine / nullification"]',
            f'    Gold["Gold: {facts["identity"]["pipeline_id"]}"]',
            f"    {previous} --> Merge --> Validate",
            "    Validate -->|valid| Gold",
            "    Validate -->|excluded| Excluded",
        ]
    )
    return "\n".join(lines)
