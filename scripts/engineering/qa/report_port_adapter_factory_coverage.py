#!/usr/bin/env python3
"""Generate port-to-adapter-to-factory coverage matrix artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "port-adapter-factory-coverage.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "port-adapter-factory-coverage.md"
)

# Shared coverage evidence path identities (python:S1192).
TEST_STRICT_ARCHITECTURE_CONTRACTS = (
    "tests/architecture/test_strict_architecture_contracts.py"
)
PATH_STORAGE_BUNDLE = "src/bioetl/composition/factories/storage/bundle.py"
PATH_STORAGE_BOOTSTRAP_ASSEMBLY = (
    "src/bioetl/composition/bootstrap/assembly/storage.py"
)
PATH_STORAGE_FACTORY = "src/bioetl/composition/factories/storage/factory.py"
TEST_STORAGE_BOOTSTRAP = (
    "tests/unit/composition/bootstrap/test_storage_bootstrap.py"
)


@dataclass(frozen=True, slots=True)
class PortCoverageSpec:
    """Expected core-port adapter/factory/test evidence."""

    port_name: str
    port_path: str
    adapter_symbols: tuple[str, ...]
    adapter_paths: tuple[str, ...]
    factory_paths: tuple[str, ...]
    test_paths: tuple[str, ...]
    notes: str = ""


TRACKED_PORTS: tuple[PortCoverageSpec, ...] = (
    PortCoverageSpec(
        port_name="DataSourcePort",
        port_path="src/bioetl/domain/ports/data_source.py",
        adapter_symbols=("ChemblAdapter", "PubChemAdapter", "UniProtAdapter"),
        adapter_paths=(
            "src/bioetl/infrastructure/adapters/chembl/client.py",
            "src/bioetl/infrastructure/adapters/pubchem/client.py",
            "src/bioetl/infrastructure/adapters/uniprot/client.py",
        ),
        factory_paths=(
            "src/bioetl/composition/providers/registration_bio.py",
            "src/bioetl/composition/factories/datasource/data_source_factory.py",
            "src/bioetl/composition/factories/datasource/pubchem.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/architecture/test_adapter_contracts.py",
            "tests/unit/composition/factories/datasource/test_data_sources.py",
        ),
    ),
    PortCoverageSpec(
        port_name="CheckpointPort",
        port_path="src/bioetl/domain/ports/runtime/checkpoint.py",
        adapter_symbols=("LocalCheckpointAdapter",),
        adapter_paths=("src/bioetl/infrastructure/checkpoint/local_checkpoint.py",),
        factory_paths=(
            "src/bioetl/composition/bootstrap/assembly/checkpoint.py",
            "src/bioetl/composition/bootstrap/cli/checkpoint.py",
            "src/bioetl/composition/factories/services/port_factories.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/unit/composition/bootstrap/test_checkpoint_bootstrap.py",
            "tests/architecture/test_port_contracts_resilience_concurrency.py",
        ),
    ),
    PortCoverageSpec(
        port_name="QuarantinePort",
        port_path="src/bioetl/domain/ports/quality/quarantine.py",
        adapter_symbols=("UnifiedQuarantineAdapter",),
        adapter_paths=("src/bioetl/infrastructure/quarantine/unified.py",),
        factory_paths=(
            "src/bioetl/composition/bootstrap/assembly/checkpoint.py",
            "src/bioetl/composition/bootstrap/cli/checkpoint.py",
            "src/bioetl/composition/factories/services/port_factories.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/unit/composition/bootstrap/test_checkpoint_bootstrap.py",
            "tests/architecture/test_quarantine_immutability.py",
        ),
    ),
    PortCoverageSpec(
        port_name="RunManifestPort",
        port_path="src/bioetl/domain/ports/control_plane/run_manifest.py",
        adapter_symbols=("FileRunManifestStore",),
        adapter_paths=(
            "src/bioetl/infrastructure/control_plane/file_run_manifest_store.py",
        ),
        factory_paths=(
            "src/bioetl/composition/bootstrap/control_plane_store_builders.py",
            "src/bioetl/composition/bootstrap/assembly/health_server.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/unit/composition/bootstrap/test_control_plane_store_builders.py",
            "tests/unit/infrastructure/control_plane/test_file_run_manifest_store.py",
        ),
    ),
    PortCoverageSpec(
        port_name="RunLedgerPort",
        port_path="src/bioetl/domain/ports/control_plane/run_ledger.py",
        adapter_symbols=("FileRunLedgerStore",),
        adapter_paths=(
            "src/bioetl/infrastructure/control_plane/file_run_ledger_store.py",
        ),
        factory_paths=(
            "src/bioetl/composition/bootstrap/control_plane_store_builders.py",
            "src/bioetl/composition/bootstrap/assembly/health_server.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/unit/composition/bootstrap/test_control_plane_store_builders.py",
            "tests/unit/infrastructure/control_plane/test_file_run_ledger_store.py",
        ),
    ),
    PortCoverageSpec(
        port_name="MetricsPort",
        port_path="src/bioetl/domain/ports/observability/metrics.py",
        adapter_symbols=("PrometheusMetrics", "NoOpMetrics"),
        adapter_paths=(
            "src/bioetl/infrastructure/observability/prometheus_metrics.py",
            "src/bioetl/domain/ports/noop/_metrics.py",
        ),
        factory_paths=(
            "src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py",
            "src/bioetl/composition/observability_resolution.py",
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            "tests/unit/composition/bootstrap/runtime/test_metrics_bootstrap.py",
            "tests/unit/infrastructure/observability/test_metrics_port_contract.py",
        ),
    ),
    PortCoverageSpec(
        port_name="ClockPort",
        port_path="src/bioetl/domain/ports/runtime/clock.py",
        adapter_symbols=("SystemClock",),
        adapter_paths=("src/bioetl/infrastructure/time/system_clock.py",),
        factory_paths=(
            "src/bioetl/composition/bootstrap/runtime/runtime_basics.py",
            "src/bioetl/composition/bootstrap/runtime/runner.py",
            "src/bioetl/composition/factories/pipeline/_runner_assembly_support.py",
        ),
        test_paths=(
            "tests/unit/infrastructure/time/test_system_clock.py",
            "tests/unit/helpers/test_clock_helpers.py",
            "tests/architecture/test_replay_time_seam_inventory.py",
        ),
    ),
    PortCoverageSpec(
        port_name="BronzeStoragePort",
        port_path="src/bioetl/domain/ports/storage/bronze_port.py",
        adapter_symbols=("StorageBundle", "BronzeWriter"),
        adapter_paths=(
            PATH_STORAGE_BUNDLE,
            "src/bioetl/infrastructure/storage/bronze_writer.py",
        ),
        factory_paths=(
            PATH_STORAGE_BOOTSTRAP_ASSEMBLY,
            PATH_STORAGE_FACTORY,
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            TEST_STORAGE_BOOTSTRAP,
            "tests/unit/composition/factories/storage/test_bronze_factory.py",
        ),
    ),
    PortCoverageSpec(
        port_name="SilverStoragePort",
        port_path="src/bioetl/domain/ports/storage/silver_port.py",
        adapter_symbols=("StorageBundle", "SilverWriter"),
        adapter_paths=(
            PATH_STORAGE_BUNDLE,
            "src/bioetl/infrastructure/storage/silver_writer.py",
        ),
        factory_paths=(
            PATH_STORAGE_BOOTSTRAP_ASSEMBLY,
            PATH_STORAGE_FACTORY,
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            TEST_STORAGE_BOOTSTRAP,
            "tests/unit/infrastructure/storage/silver_writer/test_silver_writer_schema.py",
        ),
    ),
    PortCoverageSpec(
        port_name="GoldStoragePort",
        port_path="src/bioetl/domain/ports/storage/gold_port.py",
        adapter_symbols=("StorageBundle", "GoldWriter"),
        adapter_paths=(
            PATH_STORAGE_BUNDLE,
            "src/bioetl/infrastructure/storage/gold_writer.py",
        ),
        factory_paths=(
            PATH_STORAGE_BOOTSTRAP_ASSEMBLY,
            PATH_STORAGE_FACTORY,
        ),
        test_paths=(
            TEST_STRICT_ARCHITECTURE_CONTRACTS,
            TEST_STORAGE_BOOTSTRAP,
            "tests/unit/infrastructure/schemas/test_gold.py",
        ),
    ),
)


def _exists(relative_path: str) -> bool:
    return (PROJECT_ROOT / relative_path).is_file()


def _path_mentions(path: str, symbol: str) -> bool:
    target = PROJECT_ROOT / path
    return target.is_file() and symbol in target.read_text(encoding="utf-8")


def _missing_symbol_mentions(
    paths: tuple[str, ...], symbols: tuple[str, ...]
) -> list[str]:
    missing: list[str] = []
    for symbol in symbols:
        if not any(_path_mentions(path, symbol) for path in paths):
            missing.append(symbol)
    return missing


def _missing_test_evidence(spec: PortCoverageSpec) -> list[str]:
    evidence_symbols = (spec.port_name, *spec.adapter_symbols)
    has_contract_evidence = any(
        _path_mentions(path, symbol)
        for path in spec.test_paths
        for symbol in evidence_symbols
    )
    return [] if has_contract_evidence else [spec.port_name]


def _build_row(spec: PortCoverageSpec) -> dict[str, Any]:
    missing_paths = sorted(
        path
        for path in (
            spec.port_path,
            *spec.adapter_paths,
            *spec.factory_paths,
            *spec.test_paths,
        )
        if not _exists(path)
    )
    missing_adapter_symbols = _missing_symbol_mentions(
        spec.adapter_paths, spec.adapter_symbols
    )
    missing_factory_symbols = _missing_symbol_mentions(
        spec.factory_paths, spec.adapter_symbols
    )
    missing_test_symbols = _missing_test_evidence(spec)

    missing_surfaces: list[str] = []
    if missing_paths:
        missing_surfaces.append("path")
    if missing_adapter_symbols:
        missing_surfaces.append("adapter_symbol")
    if missing_factory_symbols:
        missing_surfaces.append("factory_symbol")
    if missing_test_symbols:
        missing_surfaces.append("test_symbol")

    return {
        "port_name": spec.port_name,
        "port_path": spec.port_path,
        "adapter_symbols": list(spec.adapter_symbols),
        "adapter_paths": list(spec.adapter_paths),
        "factory_paths": list(spec.factory_paths),
        "test_paths": list(spec.test_paths),
        "notes": spec.notes,
        "missing_paths": missing_paths,
        "missing_adapter_symbols": missing_adapter_symbols,
        "missing_factory_symbols": missing_factory_symbols,
        "missing_test_symbols": missing_test_symbols,
        "missing_surfaces": missing_surfaces,
        "coverage_status": "covered" if not missing_surfaces else "missing_surfaces",
    }


def build_payload() -> dict[str, Any]:
    rows = [_build_row(spec) for spec in TRACKED_PORTS]
    unresolved = [row for row in rows if row["coverage_status"] != "covered"]
    return {
        "schema_version": "1.0.0",
        "scope": "core_active_ports",
        "row_count": len(rows),
        "covered_count": len(rows) - len(unresolved),
        "unresolved_count": len(unresolved),
        "tracked_ports": [row["port_name"] for row in rows],
        "rows": rows,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Port Adapter Factory Coverage",
        "",
        f"- schema_version: {payload['schema_version']}",
        f"- scope: {payload['scope']}",
        f"- row_count: {payload['row_count']}",
        f"- covered_count: {payload['covered_count']}",
        f"- unresolved_count: {payload['unresolved_count']}",
        "",
        "| port | status | adapters | factories | tests | missing_surfaces |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in payload["rows"]:
        missing = ", ".join(row["missing_surfaces"]) or "-"
        adapters = ", ".join(f"`{symbol}`" for symbol in row["adapter_symbols"])
        lines.append(
            "| `{port_name}` | `{coverage_status}` | {adapters} | {factory_count} | "
            "{test_count} | {missing} |".format(
                **row,
                adapters=adapters,
                factory_count=len(row["factory_paths"]),
                test_count=len(row["test_paths"]),
                missing=missing,
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_artifacts(*, json_out: Path, md_out: Path, root: Path | None = None) -> None:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        json_out = resolve_output_path(json_out, root=root)
        md_out = resolve_output_path(md_out, root=root)
    payload = build_payload()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    from scripts.engineering.common.repo_paths import REPO_ROOT

    parser = argparse.ArgumentParser(
        description="Generate port-adapter-factory coverage artifacts."
    )
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed JSON artifact drifts from generator output.",
    )
    args = parser.parse_args(argv)
    root = REPO_ROOT

    if args.check:
        from scripts.engineering.common.repo_paths import resolve_output_path

        json_out = resolve_output_path(args.json_out, root=root)
        expected = json.dumps(build_payload(), indent=2, sort_keys=True) + "\n"
        actual = json_out.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "[port-adapter-factory-coverage] artifact drift detected; "
                "regenerate with: python -m scripts.engineering.qa "
                "report-port-adapter-factory-coverage",
                file=sys.stderr,
            )
            return 1
        print("[ok] port adapter factory coverage is up to date")
        return 0

    write_artifacts(json_out=args.json_out, md_out=args.md_out, root=root)
    payload = build_payload()
    print(
        "[port-adapter-factory-coverage] "
        f"rows={payload['row_count']}; covered={payload['covered_count']}; "
        f"unresolved={payload['unresolved_count']}; json={args.json_out}; "
        f"md={args.md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
