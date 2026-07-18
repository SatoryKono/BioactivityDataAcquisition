#!/usr/bin/env python3
"""Render pipeline dataflow IR into Mermaid and companion documentation."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from scripts.diagrams.pipeline_dataflow_ir import (
    CriterionIR,
    FieldIR,
    PipelineDataflowIR,
)

DIAGRAM_FILENAMES = (
    "49-chembl-activity-dataflow.mmd",
    "50-chembl-activity-filter-criteria.mmd",
    "51a-chembl-activity-silver-fields-1.mmd",
    "51b-chembl-activity-silver-fields-2.mmd",
    "52a-chembl-activity-gold-fields-1.mmd",
    "52b-chembl-activity-gold-fields-2.mmd",
)
ARTIFACT_FILENAMES = (
    "pipeline-dataflow-ir.json",
    "fields.csv",
    "pipeline-passport.md",
)
FIELDS_PER_NODE = 5
FIELDS_PER_SHEET = 60

_INIT = (
    "%%{init: {'theme': 'neutral', 'themeVariables': "
    "{'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}, "
    "'flowchart': {'wrappingWidth': 360}}}%%"
)
_PALETTE = """    classDef source fill:#f1f5f9,stroke:#64748b,stroke-width:2px
    classDef process fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    classDef bronze fill:#fff7ed,stroke:#f59e0b,stroke-width:2px
    classDef silver fill:#f8fafc,stroke:#475569,stroke-width:2px
    classDef gold fill:#fefce8,stroke:#ca8a04,stroke-width:2px
    classDef dq fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px
    classDef warning fill:#fff1f2,stroke:#dc2626,stroke-width:2px"""


def _chunks[T](items: Sequence[T], size: int) -> list[Sequence[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _mermaid_escape(value: object) -> str:
    text = str(value).replace("&", "&amp;")
    return (
        text.replace('"', "'")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
    )


def _compact_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict) and {"min", "max"} <= set(value):
        left = "[" if value.get("include_min", True) else "("
        right = "]" if value.get("include_max", True) else ")"
        minimum = "-inf" if value.get("min") is None else str(value["min"])
        maximum = "+inf" if value.get("max") is None else str(value["max"])
        return f"{left}{minimum}, {maximum}{right}"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _criterion_line(criterion: CriterionIR) -> str:
    if criterion.operator == "is not null":
        if criterion.category == "structural":
            return _mermaid_escape(criterion.field)
        return _mermaid_escape(f"{criterion.field} present")
    if criterion.operator == "is null":
        return _mermaid_escape(f"{criterion.field} missing")
    if criterion.operator == "exclude if present":
        return _mermaid_escape(f"{criterion.field} {criterion.operator}")
    return _mermaid_escape(
        f"{criterion.field} {criterion.operator} {_compact_value(criterion.value)}"
    )


def _header(
    *,
    title: str,
    diagram_type: str,
    level: str,
    nodes: int,
    version: str,
    date: str,
) -> list[str]:
    return [
        f"%% BioETL — {title}",
        "%% Generated from the resolved chembl_activity configuration and contracts.",
        "",
        f"%% @version {version}",
        f"%% @date    {date}",
        f"%% @type    {diagram_type}",
        f"%% @level   {level}",
        f"%% @nodes   {nodes}",
        "%% @adr     ADR-002, ADR-040",
        _INIT,
    ]


def _overview(ir: PipelineDataflowIR) -> str:
    lines = _header(
        title="ChEMBL Activity Source To Silver And Gold",
        diagram_type="flowchart",
        level="Pipeline / Dataflow",
        nodes=14,
        version=ir.generator_version,
        date=ir.generated_date,
    )
    lines.extend(
        (
            "flowchart LR",
            '    API["ChEMBL activity API"]',
            f'    Query["Source query<br/>{len(ir.extraction_criteria)} criteria"]',
            '    Bronze["Bronze records<br/>raw source payload"]',
            '    Input["Input-file filter<br/>disabled"]',
            '    Transform["Activity Transformer<br/>Bronze to Silver"]',
            f'    SilverFilter["Silver structural filter<br/>{len(ir.silver_criteria)} criteria"]',
            (
                f'    DQ["Effective DQ policy<br/>{len(ir.dq.field_validations)} field rules'
                f'<br/>{len(ir.dq.cross_field_validations)} cross-field rules"]'
            ),
            f'    Silver["Silver output<br/>{len(ir.silver.fields)} fields<br/>views 51a + 51b"]',
            '    GoldTransform["Gold post-processing<br/>code-defined"]',
            f'    GoldFilter["Gold record filter<br/>{len(ir.gold_criteria)} criteria"]',
            '    GoldValidate["Gold contract validation<br/>projected schema"]',
            (
                f'    Gold["Gold output<br/>{len(ir.gold.fields)} published fields'
                f'<br/>views 52a + 52b"]'
            ),
            '    Artifacts["Pipeline passport<br/>JSON + CSV"]',
            '    Drift["CI drift check<br/>generate-dataflows --check"]',
            "",
            "    API --> Query --> Bronze --> Transform",
            "    Input -.-> Query",
            "    Transform --> SilverFilter --> DQ --> Silver",
            "    Silver --> GoldTransform --> GoldFilter --> GoldValidate --> Gold",
            "    Gold --> Artifacts --> Drift",
            "",
            "    class API,Input source",
            "    class Query,Transform,SilverFilter,GoldTransform,GoldFilter process",
            "    class Bronze bronze",
            "    class DQ dq",
            "    class Silver silver",
            "    class GoldValidate,Gold gold",
            "    class Artifacts,Drift source",
            _PALETTE,
            "",
        )
    )
    return "\n".join(lines)


def _criteria_node(node_id: str, title: str, criteria: Sequence[CriterionIR]) -> str:
    body = "<br/>".join([_mermaid_escape(title), *map(_criterion_line, criteria)])
    return f'    {node_id}["{body}"]'


def _criteria(ir: PipelineDataflowIR) -> str:
    extraction_chunks = _chunks(ir.extraction_criteria, FIELDS_PER_NODE)
    silver_required = [
        item for item in ir.silver_criteria if item.operator != "exclude if present"
    ]
    silver_exclusions = [
        item for item in ir.silver_criteria if item.operator == "exclude if present"
    ]
    silver_chunks = _chunks(silver_required, FIELDS_PER_NODE)
    gold_columns = [item for item in ir.gold_criteria if item.category == "column"]
    gold_ranges = [item for item in ir.gold_criteria if item.category == "range"]
    gold_required = [item for item in ir.gold_criteria if item.category == "structural"]
    nodes = (
        1
        + len(extraction_chunks)
        + 1
        + 1
        + len(silver_chunks)
        + (1 if silver_exclusions else 0)
        + 1
        + 3
        + 1
    )
    lines = _header(
        title="ChEMBL Activity Query And Filtering Criteria",
        diagram_type="flowchart",
        level="Pipeline / Rules",
        nodes=nodes,
        version=ir.generator_version,
        date=ir.generated_date,
    )
    lines.extend(
        (
            "flowchart LR",
            '    Source["Source query criteria<br/>applied by ChEMBL API"]',
        )
    )
    for index, chunk in enumerate(extraction_chunks, start=1):
        lines.append(_criteria_node(f"Extract{index}", f"API criteria {index}", chunk))
    lines.append(
        '    Input["Input-file filter<br/>enabled = false<br/>activity_id column"]'
    )
    lines.append('    SilverStage["Silver structural criteria"]')
    for index, chunk in enumerate(silver_chunks, start=1):
        lines.append(
            _criteria_node(f"Silver{index}", f"Required fields {index}", chunk)
        )
    if silver_exclusions:
        lines.append(
            _criteria_node("SilverExclude", "Exclusion rule", silver_exclusions)
        )
    lines.append('    GoldStage["Gold record criteria"]')
    lines.append(_criteria_node("GoldColumns", "Allowed values", gold_columns))
    lines.append(_criteria_node("GoldRanges", "Ranges", gold_ranges))
    lines.append(_criteria_node("GoldRequired", "Required values", gold_required))
    lines.append(
        f'    DQ["Effective DQ policy<br/>thresholds {ir.dq.soft_fail_threshold}'
        f" / {ir.dq.hard_fail_threshold}"
        f"<br/>{len(ir.dq.field_validations)} field rules"
        f"<br/>{len(ir.dq.cross_field_validations)} cross-field rules"
        f'<br/>{len(ir.dq.conditional_validations)} conditional rules"]'
    )
    lines.append("")
    for index in range(1, len(extraction_chunks) + 1):
        lines.append(f"    Source --> Extract{index} --> Input")
    lines.append("    Input -.-> SilverStage")
    for index in range(1, len(silver_chunks) + 1):
        lines.append(f"    SilverStage --> Silver{index} --> GoldStage")
    if silver_exclusions:
        lines.append("    SilverStage --> SilverExclude --> GoldStage")
    lines.extend(
        (
            "    GoldStage --> GoldColumns --> DQ",
            "    GoldStage --> GoldRanges --> DQ",
            "    GoldStage --> GoldRequired --> DQ",
            "",
            "    class Source,Input source",
            "    class "
            + ",".join(
                f"Extract{index}" for index in range(1, len(extraction_chunks) + 1)
            )
            + " process",
            "    class SilverStage,"
            + ",".join(f"Silver{index}" for index in range(1, len(silver_chunks) + 1))
            + " silver",
            "    class SilverExclude warning",
            "    class GoldStage,GoldColumns,GoldRanges,GoldRequired gold",
            "    class DQ dq",
            _PALETTE,
            "",
        )
    )
    assert ir.input_criteria[0].enabled is False
    return "\n".join(lines)


def _field_view(
    ir: PipelineDataflowIR,
    *,
    layer_name: str,
    fields: Sequence[FieldIR],
    sheet: int,
    total_sheets: int,
) -> str:
    chunks = _chunks(fields, FIELDS_PER_NODE)
    title = f"ChEMBL Activity {layer_name} Output Fields {sheet} Of {total_sheets}"
    lines = _header(
        title=title,
        diagram_type="flowchart",
        level=f"Pipeline / {layer_name} Contract",
        nodes=len(chunks) + 1,
        version=ir.generator_version,
        date=ir.generated_date,
    )
    lines.extend(
        (
            "flowchart TB",
            (
                f'    Layer["{layer_name} output<br/>sheet {sheet} of '
                f'{total_sheets}<br/>{len(fields)} fields"]'
            ),
        )
    )
    node_ids: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        node_id = f"Fields{index}"
        node_ids.append(node_id)
        first, last = chunk[0].ordinal, chunk[-1].ordinal
        labels = [f"Fields {first}-{last}", *(field.name for field in chunk)]
        lines.append(f'    {node_id}["{"<br/>".join(labels)}"]')
    lines.append("")
    if node_ids:
        split_at = (len(node_ids) + 1) // 2
        for column in (node_ids[:split_at], node_ids[split_at:]):
            if column:
                lines.append(f"    Layer --> {' --> '.join(column)}")
    layer_class = layer_name.lower()
    lines.extend(
        (
            "",
            f"    class Layer,{','.join(node_ids)} {layer_class}",
            f"    class {','.join(node_ids)} fieldCard",
            "    classDef fieldCard font-size:13px",
            _PALETTE,
            "",
        )
    )
    return "\n".join(lines)


def render_mermaid_views(ir: PipelineDataflowIR) -> dict[str, str]:
    """Render all canonical Mermaid source views for the pipeline."""
    silver_sheets = _chunks(ir.silver.fields, FIELDS_PER_SHEET)
    gold_sheets = _chunks(ir.gold.fields, FIELDS_PER_SHEET)
    if len(silver_sheets) != 2 or len(gold_sheets) != 2:
        raise ValueError(
            "chembl_activity field views require exactly two sheets per layer"
        )
    return {
        DIAGRAM_FILENAMES[0]: _overview(ir),
        DIAGRAM_FILENAMES[1]: _criteria(ir),
        DIAGRAM_FILENAMES[2]: _field_view(
            ir,
            layer_name="Silver",
            fields=silver_sheets[0],
            sheet=1,
            total_sheets=len(silver_sheets),
        ),
        DIAGRAM_FILENAMES[3]: _field_view(
            ir,
            layer_name="Silver",
            fields=silver_sheets[1],
            sheet=2,
            total_sheets=len(silver_sheets),
        ),
        DIAGRAM_FILENAMES[4]: _field_view(
            ir,
            layer_name="Gold",
            fields=gold_sheets[0],
            sheet=1,
            total_sheets=len(gold_sheets),
        ),
        DIAGRAM_FILENAMES[5]: _field_view(
            ir,
            layer_name="Gold",
            fields=gold_sheets[1],
            sheet=2,
            total_sheets=len(gold_sheets),
        ),
    }


def _markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _criteria_table(criteria: Iterable[CriterionIR]) -> list[str]:
    lines = [
        "| Stage | Category | Field | Operator | Value | Enabled |",
        "|---|---|---|---|---|---:|",
    ]
    for item in criteria:
        lines.append(
            "| "
            + " | ".join(
                _markdown_escape(value)
                for value in (
                    item.stage,
                    item.category,
                    item.field,
                    item.operator,
                    _compact_value(item.value),
                    str(item.enabled).lower(),
                )
            )
            + " |"
        )
    return lines


def _field_table(fields: Sequence[FieldIR]) -> list[str]:
    lines = [
        "| # | Field | Type | Nullable | Required | Group |",
        "|---:|---|---|---:|---:|---|",
    ]
    for field in fields:
        lines.append(
            f"| {field.ordinal} | `{field.name}` | `{field.data_type}` | "
            f"{str(field.nullable).lower()} | {str(field.required).lower()} | "
            f"{field.group} |"
        )
    return lines


def _dq_field_table(ir: PipelineDataflowIR) -> list[str]:
    lines = [
        "| Field | Validation | Nullable | Severity | Constraint |",
        "|---|---|---:|---|---|",
    ]
    ignored = {"field", "validation_type", "nullable", "severity", "error_message"}
    for rule in ir.dq.field_validations:
        constraint = {
            key: value
            for key, value in rule.items()
            if key not in ignored and value not in (None, [], (), "")
        }
        lines.append(
            f"| `{rule['field']}` | {rule['validation_type']} | "
            f"{str(rule['nullable']).lower()} | {rule['severity']} | "
            f"`{_markdown_escape(_compact_value(constraint))}` |"
        )
    return lines


def _dq_cross_table(ir: PipelineDataflowIR) -> list[str]:
    lines = ["| Name | Fields | Condition | Severity |", "|---|---|---|---|"]
    for rule in ir.dq.cross_field_validations:
        fields = cast("list[str]", rule["fields"])
        lines.append(
            f"| `{rule['name']}` | `{', '.join(fields)}` | "
            f"{rule['condition']} | {rule['severity']} |"
        )
    return lines


def _dq_conditional_table(ir: PipelineDataflowIR) -> list[str]:
    lines = ["| Name | When | Then |", "|---|---|---|"]
    for rule in ir.dq.conditional_validations:
        then_validations = cast("list[dict[str, object]]", rule["then_validations"])
        validators = ", ".join(
            f"{item['field']}:{item['validation_type']}" for item in then_validations
        )
        lines.append(
            f"| `{rule['name']}` | `{rule['condition_field']} "
            f"{rule['condition_operator']} {_markdown_escape(rule['condition_value'])}` | "
            f"`{validators}` |"
        )
    return lines


def _layer_summary_lines(
    *,
    name: str,
    schema_ref: str,
    include_groups: Sequence[str],
    exclude_fields: Sequence[str],
    fields: Sequence[FieldIR],
) -> list[str]:
    return [
        f"## {name} Output Fields ({len(fields)})",
        "",
        f"Schema: `{schema_ref}`  ",
        f"Included groups: `{', '.join(include_groups)}`  ",
        f"Excluded patterns: `{', '.join(exclude_fields) if exclude_fields else 'none'}`",
        "",
        *_field_table(fields),
        "",
    ]


def render_passport(ir: PipelineDataflowIR) -> str:
    """Render the human-readable pipeline passport with complete rule lists."""
    diagram_links = [
        f"- [{Path(name).stem}](../../../diagrams/architecture/svg/{Path(name).stem}.svg)"
        for name in DIAGRAM_FILENAMES
    ]
    diagnostics = [
        f"- **{item.severity.upper()} `{item.code}`** — {item.message} "
        f"Fields: `{', '.join(item.fields)}`."
        for item in ir.diagnostics
    ] or ["- No diagnostics."]
    source_lines = [
        f"- `{source.kind}`: `{source.path}`"
        + (f" — `{source.symbol}`" if source.symbol else "")
        for source in ir.sources
    ]
    methods = ", ".join(f"`{name}`" for name in ir.post_processing.code_defined_methods)
    declarative = (
        json.dumps(ir.post_processing.declarative_steps, ensure_ascii=False)
        if ir.post_processing.declarative_steps
        else "none"
    )
    lines = [
        "<!-- Generated by scripts/diagrams/generate_pipeline_dataflows.py; do not edit manually. -->",
        "",
        f"# `{ir.pipeline_name}` Pipeline Dataflow Passport",
        "",
        f"Generated: **{ir.generated_date}**  ",
        f"Generator: **{ir.generator_version}**  ",
        f"IR schema: **{ir.schema_version}**  ",
        f"Effective config SHA256: `{ir.effective_config_sha256}`  ",
        f"Effective loader: `{ir.effective_config_loader}`",
        "",
        (
            "This passport is generated from the resolved effective configuration "
            "and live schema contracts. It describes the current runtime projection; "
            "it does not widen or repair the pipeline contract."
        ),
        "",
        "## Linked Views",
        "",
        *diagram_links,
        "",
        "Machine-readable companions: [IR JSON](pipeline-dataflow-ir.json) and [field CSV](fields.csv).",
        "",
        "## Source Profile",
        "",
        f"- Profile: `{ir.source_profile.get('profile_id')}`",
        f"- Version: `{ir.source_profile.get('version')}`",
        f"- Status: `{ir.source_profile.get('status')}`",
        f"- Extraction hash: `{ir.source_profile.get('extraction_params_sha256')}`",
        f"- Description: {ir.source_profile.get('description')}",
        "",
        "## Source Query Criteria",
        "",
        *_criteria_table(ir.extraction_criteria),
        "",
        "## Input-file Criteria",
        "",
        *_criteria_table(ir.input_criteria),
        "",
        "## Silver Filtering Criteria",
        "",
        *_criteria_table(ir.silver_criteria),
        "",
        "## Gold Filtering Criteria",
        "",
        *_criteria_table(ir.gold_criteria),
        "",
        "## Post-processing",
        "",
        f"- Transformer: `{ir.post_processing.transformer_class}`",
        f"- Declarative transform steps: `{declarative}`",
        f"- Code-defined methods present: {methods or 'none'}",
        f"- Inspection policy: {ir.post_processing.inspection_policy}",
        "",
        "## Effective DQ Policy",
        "",
        f"- Soft-fail threshold: `{ir.dq.soft_fail_threshold}`",
        f"- Hard-fail threshold: `{ir.dq.hard_fail_threshold}`",
        f"- Strict validation: `{str(ir.dq.strict_validation).lower()}`",
        f"- Invalid-record policy: `{ir.dq.invalid_record_policy}`",
        "",
        "### Field validations",
        "",
        *_dq_field_table(ir),
        "",
        "### Cross-field validations",
        "",
        *_dq_cross_table(ir),
        "",
        "### Conditional validations",
        "",
        *_dq_conditional_table(ir),
        "",
        *_layer_summary_lines(
            name="Silver",
            schema_ref=ir.silver.schema_ref,
            include_groups=ir.silver.include_groups,
            exclude_fields=ir.silver.exclude_fields,
            fields=ir.silver.fields,
        ),
        *_layer_summary_lines(
            name="Gold",
            schema_ref=ir.gold.schema_ref,
            include_groups=ir.gold.include_groups,
            exclude_fields=ir.gold.exclude_fields,
            fields=ir.gold.fields,
        ),
        "## Projection Diagnostics",
        "",
        *diagnostics,
        "",
        f"Gold contract fields: **{ir.gold.contract_field_count}**. ",
        f"Current published projection: **{len(ir.gold.fields)}**.",
        "",
        "## Canonical Sources",
        "",
        *source_lines,
        "",
    ]
    return "\n".join(lines)


def render_fields_csv(ir: PipelineDataflowIR) -> str:
    """Render a machine-readable inventory for Silver and Gold output fields."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=(
            "pipeline",
            "layer",
            "ordinal",
            "field",
            "data_type",
            "nullable",
            "required",
            "group",
            "schema_source",
            "description",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    for layer_name, fields in (("silver", ir.silver.fields), ("gold", ir.gold.fields)):
        for field in fields:
            writer.writerow(
                {
                    "pipeline": ir.pipeline_name,
                    "layer": layer_name,
                    "ordinal": field.ordinal,
                    "field": field.name,
                    "data_type": field.data_type,
                    "nullable": str(field.nullable).lower(),
                    "required": str(field.required).lower(),
                    "group": field.group,
                    "schema_source": field.schema_source,
                    "description": field.description,
                }
            )
    return stream.getvalue()


def render_description_card(
    ir: PipelineDataflowIR,
    *,
    diagram_filename: str,
    title: str,
    description: str,
    level: str,
) -> str:
    """Render one governed Russian description card for a generated diagram."""
    stem = Path(diagram_filename).stem
    related = [
        f"- `{Path(name).stem}`"
        for name in DIAGRAM_FILENAMES
        if name != diagram_filename
    ]
    lines = [
        "______________________________________________________________________",
        "",
        f"Version: {ir.generator_version}",
        "Status: active",
        "Class: published",
        "Owner: BioETL Team",
        "Reviewers:",
        "",
        "- BioETL Team",
        f"  Last verified: '{ir.generated_date}'",
        "",
        "______________________________________________________________________",
        "",
        f"# {title}",
        "",
        f"- Исходная диаграмма: `architecture/{diagram_filename}`",
        f"- SVG: `architecture/svg/{stem}.svg`",
        f"- Паспорт: `generated/pipeline-dataflows/{ir.pipeline_name}/pipeline-passport.md`",
        "",
        "## Описание",
        "",
        description,
        "",
        "Диаграмма генерируется из единого типизированного IR; ручное редактирование источника не предусмотрено.",
        "",
        "## Связанные представления",
        "",
        *related,
        "",
        "## Метаданные",
        "",
        "- Тип: `flowchart`",
        f"- Уровень: `{level}`",
        f"- Дата метаданных: `{ir.generated_date}`",
        "- Источник истины: `pipeline-dataflow-ir.json`",
        "",
    ]
    return "\n".join(lines)


def render_text_outputs(
    ir: PipelineDataflowIR,
    *,
    diagram_dir: Path,
    description_dir: Path,
    artifact_dir: Path,
) -> dict[Path, str]:
    """Return every deterministic text output keyed by its destination path."""
    mermaid = render_mermaid_views(ir)
    outputs = {diagram_dir / name: content for name, content in mermaid.items()}
    descriptions = (
        (
            "ChEMBL Activity Source To Silver And Gold",
            (
                "Показывает сквозной путь записи от API ChEMBL через Bronze, "
                "структурную фильтрацию и DQ к фактическим выходам Silver и Gold."
            ),
            "Pipeline / Dataflow",
        ),
        (
            "ChEMBL Activity Query And Filtering Criteria",
            (
                "Фиксирует полный набор критериев запроса к ChEMBL API, входной "
                "фильтр, структурные правила Silver, фильтры Gold и сводку DQ."
            ),
            "Pipeline / Rules",
        ),
        (
            "ChEMBL Activity Silver Output Fields 1 Of 2",
            "Первая часть полного списка полей, реально публикуемых в слой Silver, в детерминированном порядке записи.",
            "Pipeline / Silver Contract",
        ),
        (
            "ChEMBL Activity Silver Output Fields 2 Of 2",
            "Вторая часть полного списка полей, реально публикуемых в слой Silver, в детерминированном порядке записи.",
            "Pipeline / Silver Contract",
        ),
        (
            "ChEMBL Activity Gold Output Fields 1 Of 2",
            "Первая часть фактической Gold-проекции после применения групп колонок и исключений слоя.",
            "Pipeline / Gold Contract",
        ),
        (
            "ChEMBL Activity Gold Output Fields 2 Of 2",
            "Вторая часть фактической Gold-проекции; поля контракта вне проекции перечислены отдельно в паспорте.",
            "Pipeline / Gold Contract",
        ),
    )
    for filename, (title, description, level) in zip(
        DIAGRAM_FILENAMES, descriptions, strict=True
    ):
        outputs[description_dir / f"{Path(filename).stem}.md"] = (
            render_description_card(
                ir,
                diagram_filename=filename,
                title=title,
                description=description,
                level=level,
            )
        )
    outputs[artifact_dir / ARTIFACT_FILENAMES[0]] = (
        json.dumps(ir.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    outputs[artifact_dir / ARTIFACT_FILENAMES[1]] = render_fields_csv(ir)
    outputs[artifact_dir / ARTIFACT_FILENAMES[2]] = render_passport(ir)
    return outputs


__all__ = [
    "ARTIFACT_FILENAMES",
    "DIAGRAM_FILENAMES",
    "FIELDS_PER_NODE",
    "FIELDS_PER_SHEET",
    "render_fields_csv",
    "render_mermaid_views",
    "render_passport",
    "render_text_outputs",
]
