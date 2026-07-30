"""Compact human-readable rendering for passport facts."""

from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]


def _inline(value: object) -> str:
    if value is None or value == "" or value == []:
        return "—"
    if isinstance(value, list):
        return ", ".join(f"`{item}`" for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}={item}" for key, item in sorted(value.items()))
    return f"`{value}`"


def _pipeline_markdown(facts: JsonObject, manual: dict[str, object]) -> str:
    identity = facts["identity"]
    summary = facts["summary"]
    extraction = facts["extraction"]
    silver = facts.get("silver", {})
    gold = facts.get("gold", {})
    diagnostics = facts.get("diagnostics", [])
    pipeline_id = str(identity["pipeline_id"])
    pipeline_type = str(identity["pipeline_type"])
    contract = gold.get("contract_ref") or pipeline_id
    version = gold.get("contract_version")
    contract_label = f"{contract} v{version}" if version else str(contract)
    lines = [
        f"# `{pipeline_id}`",
        "",
        "> Generated documentation projection. Do not edit manually.",
        "",
        "## Обзор",
        "",
        "| Параметр | Значение |",
        "| --- | --- |",
        f"| Typed identity `[type:{pipeline_type}]` | `{identity['typed_id']}` |",
        f"| Status | `{identity['status']}` |",
        f"| Gold contract | `{contract_label}` |",
    ]
    if identity.get("aliases"):
        lines.append(f"| Aliases | {_inline(identity['aliases'])} |")
    lines.extend(["", "## Назначение и обработка данных", ""])
    lines.extend(str(sentence) for sentence in summary["sentences"])
    resources = [
        *extraction.get("source_tables", []),
        *extraction.get("source_collections", []),
    ]
    endpoint = _inline(extraction.get("endpoint_template"))
    if extraction.get("provider_base_url") and not extraction.get("endpoint_template"):
        endpoint += f" (base URL `{extraction['provider_base_url']}`)"
    filters = (
        "; ".join(
            f"`{item['name']}`: {item['description']}"
            for item in extraction.get("filters", [])
        )
        or "Нет статических filters; используется effective runtime scope"
    )
    lines.extend(
        [
            "",
            "## Извлечение данных",
            "",
            "| Аспект | Значение |",
            "| --- | --- |",
            f"| Source | `{extraction.get('source_kind')}` · `{extraction.get('source_resource')}` |",
            f"| Method / endpoint | {_inline(extraction.get('method'))} · {endpoint} |",
            f"| Resource / tables | {_inline(resources)} |",
            f"| Filters | {filters} |",
        ]
    )
    groups = extraction.get("field_groups", [])
    if groups:
        group_text = "; ".join(
            f"`{item['name']}` ({item['field_count']} fields)" for item in groups
        )
        lines.append(f"| Selected fields | {group_text} |")
    lines.extend(["", "## Silver и Data Quality", ""])
    if silver:
        dq = silver.get("dq_execution", {})
        lines.extend(
            [
                f"- Normalization profile: `{silver.get('normalization_profile')}`.",
                f"- Partitioning: {_inline(silver.get('write', {}).get('partition_by'))}.",
                (
                    f"- DQ thresholds: soft `{dq.get('soft_fail_threshold')}`, "
                    f"hard `{dq.get('hard_fail_threshold')}`; "
                    f"invalid policy `{dq.get('invalid_record_policy')}`."
                ),
            ]
        )
    lines.extend(["", "## Gold", ""])
    validation = gold.get("contract_validation", {})
    write = gold.get("write", {})
    lines.extend(
        [
            f"- Contract: `{contract_label}`; strict validation: `{validation.get('strict', True)}`.",
            f"- Write mode: `{write.get('mode', 'configured')}`.",
        ]
    )
    if write.get("scd_config"):
        lines.append(f"- SCD2: {_inline(write['scd_config'])}.")
    exclusions = gold.get("column_projection", {}).get("exclude_fields", [])
    if exclusions:
        lines.append(f"- Technical exclusions: {_inline(exclusions)}.")
    lines.extend(
        [
            "",
            "## Операторские команды",
            "",
            "| Задача | Команда | Результат |",
            "| --- | --- | --- |",
        ]
    )
    for item in facts["operator_commands"]:
        lines.append(f"| {item['task']} | `{item['command']}` | {item['result']} |")
    lines.extend(["", "## Диаграммы", ""])
    for diagram in facts["diagrams"]:
        lines.extend(
            [
                f"### {diagram['diagram_id'].replace('_', ' ').title()}",
                "",
                "```mermaid",
                str(diagram["mermaid"]),
                "```",
                "",
            ]
        )
    if isinstance(manual.get("purpose"), str) and manual["purpose"]:
        lines.extend(["## Owner-approved context", "", str(manual["purpose"]), ""])
    lines.extend(["## Evidence", ""])
    lines.extend(
        f"- `{ref['role']}`: `{ref['path']}`" for ref in facts["source_references"]
    )
    if diagnostics:
        lines.extend(["", "## Diagnostics", ""])
        lines.extend(
            f"- `{item['severity']}` `{item['code']}`" for item in diagnostics
        )
    lines.append("")
    return "\n".join(lines)


def render_markdown(facts: JsonObject, manual: dict[str, object]) -> str:
    """Render pipeline passports compactly and retain workflow compatibility."""
    if facts["kind"] == "pipeline":
        return _pipeline_markdown(facts, manual)
    identity = facts["identity"]
    name = str(identity.get("workflow_id"))
    lines = [
        f"# {name} passport",
        "",
        "> Generated documentation projection. Do not edit manually.",
        "",
        "- Kind: `workflow`",
        f"- Typed identity: `{identity['typed_id']}`",
        f"- Schema: `{facts['passport_schema_version']}`",
        f"- Source revision: `{facts['provenance']['source_revision']}`",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(
        f"- `{ref['role']}`: `{ref['path']}`" for ref in facts["source_references"]
    )
    import json

    lines.extend(
        [
            "",
            "## Generated facts",
            "",
            "```json",
            json.dumps(facts, ensure_ascii=False, sort_keys=True, indent=2),
            "```",
            "",
            "## Diagnostics",
            "",
        ]
    )
    diagnostics = facts.get("diagnostics", [])
    lines.extend(
        (
            f"- `{item['severity']}` `{item['code']}`" for item in diagnostics
        )
        if diagnostics
        else ["- No blocking diagnostics."]
    )
    if manual:
        lines.extend(["", "## Owner-approved context", "", f"- Owner: `{manual['owner']}`"])
        for key in ("purpose", "business_context", "rationale"):
            value = manual.get(key)
            if isinstance(value, str) and value:
                lines.extend(["", f"### {key.replace('_', ' ').title()}", "", value])
        limitations = manual.get("known_limitations")
        if isinstance(limitations, list) and limitations:
            lines.extend(["", "### Known limitations", ""])
            lines.extend(f"- {item}" for item in limitations)
    lines.append("")
    return "\n".join(lines)
