"""Start the opt-in source-built presentation through the managed runtime.

The accepted native image, provider and plugin build remain unchanged. The
derived contract uses the same project, ports, networks and persistent volumes.
No environment file is written and no secret is expanded into generated YAML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import UTC, datetime
from urllib.parse import urlsplit

import yaml
from dotenv import dotenv_values

from scripts.ops.observability.grafana.generate_adaptive_dashboards import (
    generate,
    normalized_hash,
)

ROOT = Path(__file__).resolve().parents[4]
BUNDLE = ROOT / "grafana/plugins/bioetl-selectorshell-panel/dist-adaptive"


def verify_bundle(root: Path = ROOT) -> dict:
    """Reject stale compiler inputs, missing capabilities and changed output."""
    bundle = root / "grafana/plugins/bioetl-selectorshell-panel/dist-adaptive"
    if not bundle.resolve().is_relative_to(root.resolve()):
        raise ValueError("Adaptive bundle escapes the checkout")
    metadata = json.loads((bundle / "plugin.json").read_text())
    if (
        metadata.get("id") != "bioetl-selectorshell-panel"
        or metadata.get("type") != "panel"
    ):
        raise ValueError("Unexpected adaptive plugin identity")
    if "adaptive-table-v1" not in metadata["info"]["keywords"]:
        raise ValueError("Build the adaptive plugin entrypoint before starting")
    provenance = json.loads((bundle / "build-provenance.json").read_text())
    if provenance.get("capability") != "adaptive-table-v1":
        raise ValueError("Adaptive compiler provenance is missing")
    required_inputs = {
        "grafana/plugins/bioetl-selectorshell-panel/src/components/AdaptiveTable.tsx",
        "grafana/plugins/bioetl-selectorshell-panel/src/adaptive-module.ts",
        "grafana/plugins/bioetl-selectorshell-panel/package-lock.json",
        "grafana/plugins/bioetl-selectorshell-panel/webpack.adaptive.config.ts",
        "grafana/plugins/bioetl-selectorshell-panel/adaptive-build-provenance.ts",
    }
    if not required_inputs.issubset(provenance["inputs_sha256_lf"]):
        raise ValueError("Adaptive compiler provenance omits a required input")
    actual_outputs = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "build-provenance.json"
    }
    if actual_outputs != set(provenance["outputs_sha256"]) or not {
        "module.js",
        "plugin.json",
    }.issubset(actual_outputs):
        raise ValueError("Adaptive output inventory differs from its compiler receipt")
    for name, digest in provenance["inputs_sha256_lf"].items():
        target = (root / name).resolve()
        if (
            not target.is_relative_to(root.resolve())
            or normalized_hash(target) != digest
        ):
            raise ValueError(f"Adaptive plugin input changed since build: {name}")
    for name, digest in provenance["outputs_sha256"].items():
        target = (bundle / name).resolve()
        if (
            not target.is_relative_to(bundle.resolve())
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"Adaptive plugin output changed since build: {name}")
    return provenance


def prepare_contract(output: Path) -> Path:
    """Merge only the approved overlay and keep literal secret placeholders."""
    output = output.resolve()
    if not output.is_relative_to((ROOT / "reports/local").resolve()):
        raise ValueError("Adaptive runtime evidence must stay under reports/local")
    verify_bundle()
    if not generate(check=True):
        raise ValueError("Adaptive dashboards are stale; regenerate them first")
    output.mkdir(parents=True, exist_ok=True)
    captured = subprocess.check_output(
        [
            "docker",
            "compose",
            "-f",
            str(ROOT / "docker-compose.monitoring.yml"),
            "-f",
            str(ROOT / "grafana/tooling/compose.adaptive.yml"),
            "config",
            "--no-interpolate",
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
    )
    compose = json.loads(captured)
    environment = compose["services"]["grafana"]["environment"]
    if isinstance(environment, list):
        environment = dict(item.split("=", 1) for item in environment if "=" in item)
    password = environment["GF_SECURITY_ADMIN_PASSWORD"]
    if not isinstance(password, str) or not password.startswith(
        "${GF_SECURITY_ADMIN_PASSWORD"
    ):
        raise ValueError("Refusing to persist an expanded Grafana credential")
    for service in compose["services"].values():
        for mount in service.get("volumes", []):
            if mount.get("type") == "bind" and "${" not in mount["source"]:
                mount["source"] = Path(mount["source"]).resolve().as_posix()
    compose_path = output / "compose.yml"
    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")
    contract = yaml.safe_load(
        (ROOT / "configs/quality/docker_runtime_contracts.yaml").read_text()
    )
    contract["stacks"]["monitoring"]["compose_file"] = compose_path.relative_to(
        ROOT
    ).as_posix()
    contract_path = output / "runtime-contract.yml"
    contract_path.write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    return contract_path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repository_environment = dotenv_values(ROOT / ".env")
    for name, value in repository_environment.items():
        if value is not None:
            os.environ.setdefault(name, value)
    if argv[:1] == ["render"]:
        from scripts.ops.observability.grafana import rerender_grafana_screenshots
        from scripts.ops.observability.grafana.rerender_grafana_screenshots import (
            main as render_main,
        )

        render_config = rerender_grafana_screenshots._parse_args(argv[1:])
        destination = urlsplit(render_config.base_url)
        if destination.scheme not in {"http", "https"} or destination.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "The adaptive rendering wrapper requires a loopback Grafana URL"
            )
        os.environ["BIOETL_GRAFANA_PRESENTATION_PROFILE"] = "adaptive"
        os.environ["GRAFANA_PASSWORD"] = (
            repository_environment["GF_SECURITY_ADMIN_PASSWORD"] or ""
        )
        os.environ["GRAFANA_USERNAME"] = (
            repository_environment.get("GF_SECURITY_ADMIN_USER") or "admin"
        )
        started_at = datetime.now(UTC).isoformat()
        compiler = verify_bundle()
        dashboard_sources = rerender_grafana_screenshots._dashboard_source_by_uid()
        result = render_main(argv[1:])
        if (
            compiler != verify_bundle()
            or dashboard_sources
            != rerender_grafana_screenshots._dashboard_source_by_uid()
        ):
            raise RuntimeError(
                "Adaptive inputs changed during capture; rerun in a fresh directory"
            )
        rerender_grafana_screenshots._verify_adaptive_runtime(render_config)
        proof = {
            "status": "VERIFIED" if result == 0 else "CAPTURE_FAILED",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "base_url": render_config.base_url,
            "compiler_receipt": compiler,
            "dashboard_sources": dashboard_sources,
            "served_module_sha256": compiler["outputs_sha256"]["module.js"],
            "render_exit": result,
        }
        (render_config.output_dir / "adaptive-runtime-proof.json").write_text(
            json.dumps(proof, indent=2) + "\n", encoding="utf-8"
        )
        return result
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("prepare", "start", "recover", "status"),
        default="recover",
        nargs="?",
    )
    parser.add_argument(
        "--report-dir", type=Path, default=ROOT / "reports/local/adaptive-monitoring"
    )
    args = parser.parse_args(argv)
    contract = prepare_contract(args.report_dir)
    if args.action == "prepare":
        print(f"Prepared adaptive runtime contract: {contract}")
        return 0
    from scripts.ops.runtime.docker.runtime_manager import main as runtime_main

    return runtime_main(
        [
            args.action,
            "--stack",
            "monitoring",
            "--contract",
            str(contract),
            "--report-dir",
            str(args.report_dir / "runtime"),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
