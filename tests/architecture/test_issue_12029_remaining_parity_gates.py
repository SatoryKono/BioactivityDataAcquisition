"""Remaining #12029 parity gates: gold field tokens, port docstrings, SPECS.

Each gate compares two surfaces in both directions. Synthetic copies with an
extra token, a deleted token, or a renamed token must fail the same comparison
the live surfaces pass.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from bioetl.domain.contracts import gold as gold_contracts
from bioetl.domain.normalization._reference_id_registry import (
    _REFERENCE_IDENTIFIER_FAMILY_SPECS,
)
from bioetl.domain.normalization.reference_ids import (
    _REFERENCE_IDENTIFIER_NORMALIZERS,
)

pytestmark = pytest.mark.architecture

_GOLD_DOC = Path("docs/04-reference/contracts/gold-schemas.md")
_PORTS_ROOT = Path("src/bioetl")
_REGISTRY_HEADING = "## Field Token Registry"
_FIELD_TOKEN_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
_REGISTRY_BULLET_RE = re.compile(r"^- `([A-Za-z_][A-Za-z0-9_]*)`$")
_ARGS_SECTION_TITLES = {"Args:", "Arguments:", "Parameters:"}
_DOC_SECTION_RE = re.compile(
    r"^(?:Args|Arguments|Parameters|Returns|Raises|Yields|Note|Notes|"
    r"Examples|Example|Warning|Warnings)\s*:?\s*$"
)
_DOC_PARAM_RE = re.compile(r"^(\*{0,2}[A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?\s*:")
_PUBLIC_DUNDERS = {"__enter__", "__exit__", "__aenter__", "__aexit__"}

# Narrative headings are summaries. Their field/filter tokens must be a subset
# of the Pandera columns. SCD2 write-mode columns and query examples are not
# Gold schema inventories and stay outside this comparison.
_NARRATIVE_SCHEMA_HEADINGS: dict[str, tuple[str, ...]] = {
    "chembl_activity": ("ChEMBLActivityGoldSchema",),
    "chembl_molecule": ("ChEMBLMoleculeGoldSchema",),
    "chembl_assay": ("ChEMBLAssayGoldSchema",),
    "chembl_target": ("ChEMBLTargetGoldSchema",),
    "chembl_target_component": ("ChEMBLTargetComponentGoldSchema",),
    "chembl_publication": ("ChEMBLPublicationGoldSchema",),
    "chembl_compound_record": ("ChEMBLCompoundRecordGoldSchema",),
    "chembl_cell_line": ("ChEMBLCellLineGoldSchema",),
    "pubchem_compound": ("PubChemCompoundGoldSchema",),
    "uniprot_protein": ("UniProtProteinGoldSchema",),
    "pubmed_publication": ("PubMedPublicationGoldSchema",),
    "crossref_publication": ("CrossRefPublicationGoldSchema",),
    "openalex_publication": ("OpenAlexPublicationGoldSchema",),
    "semanticscholar_publication": ("SemanticScholarPublicationGoldSchema",),
    "Общие поля для всех Composite-схем": (
        "CompositeActivityGoldSchema",
        "CompositeAssayGoldSchema",
        "CompositeMoleculeGoldSchema",
        "CompositePublicationGoldSchema",
        "CompositeTargetGoldSchema",
    ),
    "Поля линейности (composite lineage)": (
        "CompositeActivityGoldSchema",
        "CompositeAssayGoldSchema",
        "CompositePublicationGoldSchema",
        "CompositeTargetGoldSchema",
    ),
    "composite_publication (дополнительные поля)": ("CompositePublicationGoldSchema",),
}

# Docstrings on this list do not declare Args/Arguments/Parameters tokens.
# Comparing them to signatures would invent a contract the text does not state.
# Methods that do declare those sections are checked in both directions.
PORT_DOCSTRING_ACCEPTED_RISK_REASON = (
    "Public port methods with parameters and no Args/Arguments/Parameters "
    "section do not declare parameter tokens, so signature comparison is not "
    "possible without inventing a contract."
)
PORT_DOCSTRING_ACCEPTED_RISKS: tuple[str, ...] = (
    "application/ports/control_plane.py:ControlPlaneArtifactLifecycleStoreProtocol.apply",
    "application/ports/control_plane.py:ControlPlaneArtifactLifecycleStoreProtocol.plan",
    "application/ports/control_plane.py:ForensicRunDiffServiceProtocol.compare",
    "application/ports/control_plane.py:HistoricalReplayClosureServiceProtocol.build_closure_report",
    "application/ports/control_plane.py:HistoricalReplayCorpusServiceProtocol.certify_retained_corpus",
    "application/ports/control_plane.py:HistoricalReplayUniverseServiceProtocol.build_universe_closure_report",
    "application/ports/control_plane.py:LineageInspectionServiceProtocol.explain_run",
    "application/ports/control_plane.py:LineageInspectionServiceProtocol.show_fragment",
    "application/ports/control_plane.py:LineageInspectionServiceProtocol.trace",
    "application/ports/control_plane.py:RunManifestInspectionServiceProtocol.diff",
    "application/ports/control_plane.py:RunManifestInspectionServiceProtocol.show",
    "application/ports/control_plane.py:RunManifestInspectionServiceProtocol.verify",
    "application/ports/control_plane.py:WorkflowInspectionServiceProtocol.inspect_latest",
    "application/ports/control_plane.py:WorkflowInspectionServiceProtocol.inspect_run_id",
    "application/ports/dq.py:DQDetectorConfig.set_threshold",
    "application/ports/health.py:HealthServiceProtocol.check_providers",
    "application/ports/metrics.py:MetricsService.delete_from_gateway",
    "application/ports/metrics.py:MetricsService.push_to_gateway",
    "application/ports/metrics.py:MetricsService.start",
    "application/ports/operations.py:AuditInspectionServiceProtocol.inspect_run",
    "application/ports/operations.py:AuditInspectionServiceProtocol.inspect_table",
    "application/ports/operations.py:AuditInspectionServiceProtocol.list_entries",
    "application/ports/operations.py:CheckpointServiceProtocol.delete_checkpoint",
    "application/ports/operations.py:CheckpointServiceProtocol.get_checkpoint",
    "application/ports/operations.py:CheckpointServiceProtocol.get_checkpoint_for_manifest_id",
    "application/ports/operations.py:CheckpointServiceProtocol.get_checkpoint_for_run",
    "application/ports/operations.py:ConfigServiceProtocol.check_config_compatibility",
    "application/ports/operations.py:ConfigServiceProtocol.get_dq_config",
    "application/ports/operations.py:ConfigServiceProtocol.get_effective_config_artifact",
    "application/ports/operations.py:ConfigServiceProtocol.get_pipeline_yaml_config",
    "application/ports/operations.py:ConfigServiceProtocol.load_pipeline_config",
    "application/ports/operations.py:ConfigServiceProtocol.validate_dq_config",
    "application/ports/operations.py:ConfigServiceProtocol.validate_pipeline_config",
    "application/ports/operations.py:ContractMigrationServiceProtocol.plan_pipeline",
    "application/ports/operations.py:ExportServiceProtocol.export",
    "application/ports/operations.py:ExportServiceProtocol.list_tables",
    "application/ports/operations.py:ExportServiceProtocol.preview",
    "application/ports/operations.py:LockServiceProtocol.check_lock",
    "application/ports/operations.py:LockServiceProtocol.force_release_all",
    "application/ports/operations.py:LockServiceProtocol.release_lock",
    "application/ports/operations.py:ObservabilityWorkflowServiceProtocol.inspect_audit_run",
    "application/ports/operations.py:ObservabilityWorkflowServiceProtocol.inspect_checkpoint_workflow",
    "application/ports/operations.py:ObservabilityWorkflowServiceProtocol.inspect_manifest_dossier",
    "application/ports/operations.py:ObservabilityWorkflowServiceProtocol.inspect_run_dossier",
    "application/ports/operations.py:VacuumServiceProtocol.collect_tables",
    "application/ports/operations.py:VacuumServiceProtocol.vacuum_all",
    "application/ports/operations.py:VacuumServiceProtocol.vacuum_table",
    "application/ports/pipeline.py:BaseServicesFactoryProtocol.create_common_services",
    "application/ports/pipeline.py:PipelineRunnerProtocol.attach_run_ledger_service",
    "application/ports/pipeline_registry.py:PipelineRegistryProtocol.register_factory",
    "application/ports/providers.py:ProviderDataSourceAccessProtocol.build_data_source_creator",
    "application/ports/providers.py:ProviderDataSourceAccessProtocol.create_adapter",
    "application/ports/providers.py:ProviderDataSourceAccessProtocol.create_data_source",
    "application/ports/providers.py:ProviderDataSourceAccessProtocol.get_http_config",
    "application/ports/providers.py:ProviderRegistrarProtocol.is_registered",
    "application/ports/providers.py:ProviderRegistrarProtocol.register",
    "application/ports/storage.py:GoldMergedWriteProtocol.write_gold_merged",
    "application/ports/storage.py:SilverMergedWriteProtocol.write_silver_merged",
    "application/ports/storage.py:StorageFactoryProtocol.create",
    "domain/ports/control_plane/artifact_byte_comparison.py:ArtifactByteComparisonPort.compare_artifacts",
    "domain/ports/control_plane/contract_evidence.py:ContractEvidenceRecorderPort.record",
    "domain/ports/control_plane/effective_config_artifact.py:EffectiveConfigArtifactStorePort.diff_occurrences_by_run_id",
    "domain/ports/control_plane/effective_config_artifact.py:EffectiveConfigArtifactStorePort.get",
    "domain/ports/control_plane/effective_config_artifact.py:EffectiveConfigArtifactStorePort.get_by_run_id",
    "domain/ports/control_plane/effective_config_artifact.py:EffectiveConfigArtifactStorePort.get_occurrence_by_run_id",
    "domain/ports/control_plane/lineage.py:LineageStorePort.get",
    "domain/ports/control_plane/lineage.py:LineageStorePort.get_occurrence",
    "domain/ports/control_plane/lineage.py:LineageStorePort.list_by_manifest_id",
    "domain/ports/control_plane/lineage.py:LineageStorePort.list_by_node_id",
    "domain/ports/control_plane/lineage.py:LineageStorePort.list_by_run_id",
    "domain/ports/control_plane/lineage.py:LineageStorePort.save",
    "domain/ports/control_plane/run_ledger.py:RunLedgerPort.append",
    "domain/ports/control_plane/run_ledger.py:RunLedgerPort.list_entries",
    "domain/ports/control_plane/run_ledger.py:RunLedgerPort.list_entries_after",
    "domain/ports/control_plane/run_ledger.py:RunLedgerPort.list_entries_by_run_id",
    "domain/ports/control_plane/run_manifest.py:RawRunManifestInspectionPort.inspect_raw_manifest",
    "domain/ports/control_plane/run_manifest.py:RunManifestPort.get",
    "domain/ports/control_plane/run_manifest.py:RunManifestPort.get_by_run_id",
    "domain/ports/control_plane/run_manifest.py:RunManifestPort.get_latest_for_scope",
    "domain/ports/control_plane/run_manifest.py:RunManifestPort.save",
    "domain/ports/control_plane/workflow_execution_state.py:WorkflowExecutionStatePort.get_by_manifest_id",
    "domain/ports/control_plane/workflow_execution_state.py:WorkflowExecutionStatePort.get_by_run_id",
    "domain/ports/control_plane/workflow_execution_state.py:WorkflowExecutionStatePort.get_latest",
    "domain/ports/control_plane/workflow_execution_state.py:WorkflowExecutionStatePort.save",
    "domain/ports/control_plane/workflow_ledger.py:WorkflowLedgerPort.append",
    "domain/ports/control_plane/workflow_ledger.py:WorkflowLedgerPort.list_entries",
    "domain/ports/control_plane/workflow_ledger.py:WorkflowLedgerPort.list_entries_by_run_id",
    "domain/ports/control_plane/workflow_manifest.py:WorkflowManifestPort.get",
    "domain/ports/control_plane/workflow_manifest.py:WorkflowManifestPort.get_by_run_id",
    "domain/ports/control_plane/workflow_manifest.py:WorkflowManifestPort.save",
    "domain/ports/data_source.py:DataSourcePort.__aexit__",
    "domain/ports/data_source.py:PublicationTermEnrichmentPort.enrich_many",
    "domain/ports/export.py:DebugExportPort.write_pack",
    "domain/ports/export.py:ExportCatalogPort.list_tables",
    "domain/ports/export.py:ExportCatalogPort.resolve_table_path",
    "domain/ports/export.py:ExportWriterPort.fingerprint_file",
    "domain/ports/export.py:ExportWriterPort.write_export",
    "domain/ports/export.py:ExportWriterPort.write_manifest",
    "domain/ports/idmapping.py:IDMappingPort.__aexit__",
    "domain/ports/metadata/writer.py:MetadataWriterPort.finalize_gold_metadata",
    "domain/ports/metadata/writer.py:MetadataWriterPort.finalize_silver_metadata",
    "domain/ports/observability/metrics.py:MetricsPublisherPort.delete_from_gateway",
    "domain/ports/observability/metrics.py:MetricsPublisherPort.push_to_gateway",
    "domain/ports/observability/tracing.py:SpanHandle.__exit__",
    "domain/ports/observability/tracing.py:SpanHandle.add_event",
    "domain/ports/observability/tracing.py:SpanHandle.record_exception",
    "domain/ports/observability/tracing.py:SpanHandle.set_attribute",
    "domain/ports/observability/tracing.py:TracerHandle.start_as_current_span",
    "domain/ports/protein_classification.py:ProteinClassificationPort.get_component_classifications",
    "domain/ports/publication_strategy.py:DataExtractorStrategy.extract_business_data",
    "domain/ports/publication_strategy.py:DataExtractorStrategy.pre_extract_validation",
    "domain/ports/publication_strategy.py:IdentifierResolverStrategy.validate_primary_id",
    "domain/ports/publication_strategy.py:PublicationMetadataStrategy.post_process_silver_record",
    "domain/ports/quality/quarantine.py:QuarantinePort.get_filtered_filter_options",
    "domain/ports/quality/quarantine.py:QuarantinePort.get_filtered_record",
    "domain/ports/quality/quarantine.py:QuarantinePort.get_filtered_stats",
    "domain/ports/quality/quarantine.py:QuarantinePort.get_filtered_timeseries",
    "domain/ports/quality/quarantine.py:QuarantinePort.get_record",
    "domain/ports/quality/quarantine.py:QuarantinePort.list_filtered_records",
    "domain/ports/runtime/checkpoint.py:CheckpointPort.load_for_manifest_id",
    "domain/ports/runtime/checkpoint.py:CheckpointPort.load_for_run",
    "domain/ports/stage_accounting.py:StageAccountingPort.mark_instrumented",
    "domain/ports/stage_accounting.py:StageAccountingPort.record_in",
    "domain/ports/stage_accounting.py:StageAccountingPort.record_out",
    "domain/ports/stage_accounting.py:StageAccountingPort.record_removal",
    "domain/ports/stage_accounting.py:StageAccountingPort.snapshot_funnel",
    "domain/ports/stage_accounting.py:StageAccountingPort.snapshot_layers_from_metrics",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.is_dir",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.is_file",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.iterdir",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.mkdir",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.mtime",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.read_identity_text",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.read_text",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.read_text_prefix",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.remove_tree",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.sha256",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.write_synced_text",
    "domain/ports/storage/run_report_store.py:RunReportStorePort.write_text",
    "domain/ports/storage/silver_port.py:SilverStoragePort.write_silver",
    "domain/ports/workflow_foreign_key_reconciliation.py:ForeignKeyReconciliationPort.reconcile_foreign_keys",
    "domain/ports/workflow_row_reconciliation.py:RowReconciliationPort.reconcile_rows",
)


def code_gold_schema_fields() -> dict[str, set[str]]:
    """Return Pandera output column tokens for every exported Gold schema."""
    fields: dict[str, set[str]] = {}
    for name in gold_contracts.__all__:
        schema_cls = getattr(gold_contracts, name)
        if isinstance(schema_cls, type) and hasattr(schema_cls, "to_schema"):
            fields[name] = set(schema_cls.to_schema().columns)
    return fields


def parse_field_token_registry(text: str) -> dict[str, set[str]]:
    """Return schema name -> field tokens from the gold-schemas registry."""
    lines = text.splitlines()
    try:
        start = lines.index(_REGISTRY_HEADING) + 1
    except ValueError as exc:
        raise AssertionError(
            "docs/04-reference/contracts/gold-schemas.md is missing "
            "Field Token Registry"
        ) from exc
    registry: dict[str, set[str]] = {}
    current: str | None = None
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("### "):
            current = line[4:].strip()
            if current in registry:
                raise AssertionError(f"duplicate registry schema {current}")
            registry[current] = set()
            continue
        if current is None or not line.strip():
            continue
        match = _REGISTRY_BULLET_RE.match(line.strip())
        if match is None:
            continue
        token = match.group(1)
        if token in registry[current]:
            raise AssertionError(f"duplicate field token {current}.{token}")
        registry[current].add(token)
    return registry


def _first_table_cell(line: str) -> str | None:
    if not line.startswith("|"):
        return None
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells:
        return None
    return cells[0]


def _is_separator_row(line: str) -> bool:
    return set(line.replace("|", "").strip()) <= set("-: ")


def parse_narrative_field_tokens(
    text: str,
    *,
    provider_schemas: tuple[str, ...],
) -> dict[str, set[str]]:
    """Return schema name -> field tokens declared by summary tables."""
    documented: dict[str, set[str]] = {}
    h2: str | None = None
    h4: str | None = None
    in_field_table = False
    for line in text.splitlines():
        if line.startswith("## "):
            h2 = line[3:].strip()
            h4 = None
            in_field_table = False
            continue
        if line.startswith("#### "):
            h4 = line[5:].strip()
            in_field_table = False
            continue
        if line.startswith("### "):
            in_field_table = False
            continue
        if not in_field_table:
            header = _first_table_cell(line)
            if header in {"Поле", "Поле (alias)", "Фильтр"}:
                in_field_table = True
            continue
        if not line.startswith("|"):
            in_field_table = False
            continue
        if _is_separator_row(line):
            continue
        cell = _first_table_cell(line) or ""
        tokens = set(_FIELD_TOKEN_RE.findall(cell))
        if not tokens:
            continue
        if h2 == "Системные поля":
            targets = provider_schemas
        elif h4 in _NARRATIVE_SCHEMA_HEADINGS:
            targets = _NARRATIVE_SCHEMA_HEADINGS[h4]
        else:
            continue
        for target in targets:
            documented.setdefault(target, set()).update(tokens)
    return documented


def assert_gold_field_parity(text: str) -> None:
    """Fail when registry or narrative field tokens diverge from schemas."""
    actual = code_gold_schema_fields()
    registry = parse_field_token_registry(text)
    missing_schemas = sorted(set(actual) - set(registry))
    extra_schemas = sorted(set(registry) - set(actual))
    if missing_schemas or extra_schemas:
        raise AssertionError(
            "gold schema registry mismatch: "
            f"missing={missing_schemas} extra={extra_schemas}"
        )
    for name, columns in actual.items():
        documented = registry[name]
        missing = sorted(columns - documented)
        extra = sorted(documented - columns)
        if missing or extra:
            raise AssertionError(
                f"{name} field token mismatch: missing={missing} extra={extra}"
            )
    provider_schemas = tuple(
        name for name in sorted(actual) if not name.startswith("Composite")
    )
    narrative = parse_narrative_field_tokens(
        text,
        provider_schemas=provider_schemas,
    )
    for name, tokens in narrative.items():
        extra = sorted(tokens - actual[name])
        if extra:
            raise AssertionError(
                f"{name} narrative field tokens absent from schema: {extra}"
            )


def _registry_block(text: str, schema_name: str) -> tuple[int, int]:
    lines = text.splitlines()
    start = None
    end = len(lines)
    for index, line in enumerate(lines):
        if line == f"### {schema_name}":
            start = index
            continue
        if start is not None and index > start and line.startswith("### "):
            end = index
            break
    if start is None:
        raise AssertionError(f"registry block missing for {schema_name}")
    return start, end


def _mutate_registry_block(
    text: str,
    schema_name: str,
    *,
    add: str | None = None,
    remove: str | None = None,
    rename: tuple[str, str] | None = None,
) -> str:
    lines = text.splitlines()
    start, end = _registry_block(text, schema_name)
    block = lines[start:end]
    if remove is not None:
        bullet = f"- `{remove}`"
        block = [line for line in block if line.strip() != bullet]
    if rename is not None:
        old, new = rename
        block = [
            f"- `{new}`" if line.strip() == f"- `{old}`" else line for line in block
        ]
    if add is not None:
        block = [*block, f"- `{add}`"]
    return "\n".join([*lines[:start], *block, *lines[end:]]) + "\n"


@dataclass(frozen=True)
class PortMethodContract:
    """One public port method and the parameter tokens its docstring declares."""

    qualified: str
    signature: tuple[str, ...]
    documented: tuple[str, ...] | None


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _is_port_class(node: ast.ClassDef) -> bool:
    if node.name.endswith("Port"):
        return True
    return any(_base_name(base) == "Protocol" for base in node.bases)


def _is_public_port_method(node: ast.stmt) -> bool:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    return not node.name.startswith("_") or node.name in _PUBLIC_DUNDERS


def signature_parameter_tokens(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    """Return declared parameter tokens, including *args and **kwargs."""
    names: list[str] = []
    for arg in [*method.args.posonlyargs, *method.args.args]:
        if arg.arg not in {"self", "cls"}:
            names.append(arg.arg)
    if method.args.vararg is not None:
        names.append("*" + method.args.vararg.arg)
    names.extend(arg.arg for arg in method.args.kwonlyargs)
    if method.args.kwarg is not None:
        names.append("**" + method.args.kwarg.arg)
    return tuple(names)


def documented_parameter_tokens(docstring: str | None) -> tuple[str, ...] | None:
    """Return Args tokens, or None when the docstring declares no parameter list."""
    if docstring is None:
        return None
    lines = docstring.splitlines()
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    base = min(indents) if indents else 0
    normalized: list[str] = []
    for line in lines:
        if line.startswith(" " * base):
            normalized.append(line[base:])
        else:
            normalized.append(line)
    start = None
    for index, line in enumerate(normalized):
        if line.strip() in _ARGS_SECTION_TITLES:
            start = index + 1
            break
    if start is None:
        return None
    names: list[str] = []
    param_indent: int | None = None
    for line in normalized[start:]:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if _DOC_SECTION_RE.match(stripped) and indent == 0:
            break
        if param_indent is None:
            param_indent = indent
        if indent < param_indent:
            break
        if indent > param_indent:
            continue
        match = _DOC_PARAM_RE.match(stripped)
        if match is None:
            raise AssertionError(f"unparsed port Args line: {stripped}")
        names.append(match.group(1))
    return tuple(names)


def port_methods_from_source(
    source: str, *, filename: str
) -> tuple[PortMethodContract, ...]:
    """Collect public port methods from one Python source string."""
    tree = ast.parse(source, filename=filename)
    methods: list[PortMethodContract] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not _is_port_class(node):
            continue
        for item in node.body:
            if not _is_public_port_method(item):
                continue
            assert isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            methods.append(
                PortMethodContract(
                    qualified=f"{filename}:{node.name}.{item.name}",
                    signature=signature_parameter_tokens(item),
                    documented=documented_parameter_tokens(ast.get_docstring(item)),
                )
            )
    return tuple(methods)


def collect_port_methods() -> tuple[PortMethodContract, ...]:
    """Collect public methods from port modules under src/bioetl."""
    methods: list[PortMethodContract] = []
    for path in sorted(_PORTS_ROOT.rglob("*.py")):
        if "ports" not in path.parts:
            continue
        relative = path.relative_to(_PORTS_ROOT).as_posix()
        methods.extend(
            port_methods_from_source(
                path.read_text(encoding="utf-8"),
                filename=relative,
            )
        )
    return tuple(methods)


def uncompared_port_methods(
    methods: tuple[PortMethodContract, ...],
) -> tuple[str, ...]:
    """Return methods whose docstrings declare no parameter contract."""
    return tuple(
        sorted(
            method.qualified
            for method in methods
            if method.signature and method.documented is None
        )
    )


def assert_parameter_tokens_match(
    signature: tuple[str, ...],
    documented: tuple[str, ...],
) -> None:
    """Fail when docstring parameter tokens differ from the signature."""
    signature_tokens = set(signature)
    documented_tokens = set(documented)
    if signature_tokens == documented_tokens:
        return
    raise AssertionError(
        "port docstring parameter mismatch: "
        f"signature-only={sorted(signature_tokens - documented_tokens)} "
        f"docstring-only={sorted(documented_tokens - signature_tokens)}"
    )


def normalizer_mapping_gaps(
    mapping: dict[str, object],
    specs: tuple[tuple[str, str, str, str, str], ...],
) -> tuple[list[str], list[str]]:
    """Return SPECS keys missing from mapping, then mapping keys missing from SPECS."""
    unlabeled = sorted(spec[0] for spec in specs if not spec[3])
    if unlabeled:
        raise AssertionError(f"SPECS rows missing normalizer mapping keys: {unlabeled}")
    spec_keys = {spec[3] for spec in specs}
    mapping_keys = set(mapping)
    missing = sorted(spec_keys - mapping_keys)
    extra = sorted(mapping_keys - spec_keys)
    return missing, extra


def assert_normalizer_mapping_matches_specs(
    mapping: dict[str, object],
    specs: tuple[tuple[str, str, str, str, str], ...],
) -> None:
    """Fail when normalizer mapping and SPECS keys are not the same set."""
    missing, extra = normalizer_mapping_gaps(mapping, specs)
    if missing or extra:
        raise AssertionError(
            "normalizer mapping/SPECS mismatch: "
            f"specs-without-mapping={missing} mapping-without-specs={extra}"
        )


def test_gold_schema_field_tokens_match_code() -> None:
    assert_gold_field_parity(_GOLD_DOC.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("add", "not_a_gold_field"),
        ("remove", "activity_id"),
        ("rename", "activity_id_renamed"),
    ],
)
def test_gold_schema_field_token_drift_is_rejected(
    mutation: str,
    match: str,
) -> None:
    text = _GOLD_DOC.read_text(encoding="utf-8")
    if mutation == "add":
        mutated = _mutate_registry_block(
            text,
            "ChEMBLActivityGoldSchema",
            add="not_a_gold_field",
        )
    elif mutation == "remove":
        mutated = _mutate_registry_block(
            text,
            "ChEMBLActivityGoldSchema",
            remove="activity_id",
        )
    else:
        mutated = _mutate_registry_block(
            text,
            "ChEMBLActivityGoldSchema",
            rename=("activity_id", "activity_id_renamed"),
        )
    with pytest.raises(AssertionError, match=match):
        assert_gold_field_parity(mutated)


def test_port_docstrings_match_declared_signatures() -> None:
    assert PORT_DOCSTRING_ACCEPTED_RISK_REASON
    methods = collect_port_methods()
    assert uncompared_port_methods(methods) == PORT_DOCSTRING_ACCEPTED_RISKS
    for method in methods:
        if method.documented is None:
            continue
        assert_parameter_tokens_match(method.signature, method.documented)


_PORT_SAMPLE = '''
class ExamplePort:
    def write(self, table_name: str, *, mode: str = "overwrite") -> None:
        """Write rows.

        Args:
            table_name: Destination table.
            mode: Write mode.
        """
'''


def _sample_method(source: str) -> PortMethodContract:
    methods = port_methods_from_source(source, filename="example.py")
    assert len(methods) == 1
    return methods[0]


def test_port_docstring_sample_matches() -> None:
    method = _sample_method(_PORT_SAMPLE)
    assert method.documented is not None
    assert_parameter_tokens_match(method.signature, method.documented)


def test_port_docstring_extra_token_is_rejected() -> None:
    source = _PORT_SAMPLE.replace(
        "            mode: Write mode.\n",
        "            mode: Write mode.\n            extra: Synthetic drift.\n",
    )
    method = _sample_method(source)
    assert method.documented is not None
    with pytest.raises(AssertionError, match="extra"):
        assert_parameter_tokens_match(method.signature, method.documented)


def test_port_docstring_deleted_token_is_rejected() -> None:
    source = _PORT_SAMPLE.replace("            mode: Write mode.\n", "")
    method = _sample_method(source)
    assert method.documented is not None
    with pytest.raises(AssertionError, match="mode"):
        assert_parameter_tokens_match(method.signature, method.documented)


def test_port_docstring_renamed_token_is_rejected() -> None:
    source = _PORT_SAMPLE.replace("mode: Write mode.", "write_mode: Write mode.")
    method = _sample_method(source)
    assert method.documented is not None
    with pytest.raises(AssertionError, match="write_mode"):
        assert_parameter_tokens_match(method.signature, method.documented)


def test_normalizer_mapping_matches_specs() -> None:
    assert_normalizer_mapping_matches_specs(
        dict(_REFERENCE_IDENTIFIER_NORMALIZERS),
        _REFERENCE_IDENTIFIER_FAMILY_SPECS,
    )


def test_normalizer_mapping_without_specs_is_rejected() -> None:
    mapping = dict(_REFERENCE_IDENTIFIER_NORMALIZERS)
    mapping["unused_key"] = None
    with pytest.raises(AssertionError, match="unused_key"):
        assert_normalizer_mapping_matches_specs(
            mapping,
            _REFERENCE_IDENTIFIER_FAMILY_SPECS,
        )


def test_specs_without_normalizer_mapping_is_rejected() -> None:
    mapping = dict(_REFERENCE_IDENTIFIER_NORMALIZERS)
    del mapping["doi"]
    with pytest.raises(AssertionError, match="doi"):
        assert_normalizer_mapping_matches_specs(
            mapping,
            _REFERENCE_IDENTIFIER_FAMILY_SPECS,
        )


def test_renamed_normalizer_spec_token_is_rejected() -> None:
    specs = tuple(
        (spec[0], spec[1], spec[2], "doi_renamed", spec[4])
        if spec[3] == "doi"
        else spec
        for spec in _REFERENCE_IDENTIFIER_FAMILY_SPECS
    )
    with pytest.raises(AssertionError, match="doi_renamed"):
        assert_normalizer_mapping_matches_specs(
            dict(_REFERENCE_IDENTIFIER_NORMALIZERS),
            specs,
        )
