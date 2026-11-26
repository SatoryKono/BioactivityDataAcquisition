"""Run an isolated BioETL attempt, optionally publishing and checking its reports."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bioetl.composition.observability_runtime import create_run_report_store
from filelock import FileLock

from scripts.ops.observability.campaign_report_artifacts import (
    collect_reports,
    publish_reports,
    read_json,
)
from scripts.ops.observability.campaign_report_visibility import DashboardAccess
from scripts.ops.observability.validate_live_observability import _load_repo_environment

REPO_ROOT = Path(__file__).resolve().parents[3]
RECEIPT = "publication.json"


def _save(output: Path, receipt: dict) -> None:
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    create_run_report_store().write_text(str(output / RECEIPT), text)


def _inside(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    if resolved == base or not resolved.is_relative_to(base):
        raise ValueError(f"Expected a directory inside {base}: {path}")
    return resolved


def _publish(
    output: Path,
    receipt: dict,
    *,
    target: Path,
    relative_data_root: str,
    access: DashboardAccess,
    source_id: str,
    query: dict,
) -> int:
    receipt["publication_status"] = "pending"
    receipt.pop("publication_error", None)
    receipt["visibility_errors"] = {}
    reports = collect_reports(
        output / "run-reports", kind=receipt["kind"], owner=receipt["owner"]
    )
    expected = [run.label for run in sorted(reports)]
    if receipt.get("expected_reports", expected) != expected:
        raise ValueError("Staged run identities changed since the original attempt")
    receipt.update(expected_reports=expected, missing_reports=expected)
    _save(output, receipt)
    publish_reports(
        output / "run-reports",
        target,
        reports,
        source_id=source_id,
        relative_data_root=relative_data_root,
    )
    receipt["publication_status"] = "published_unverified"
    _save(output, receipt)
    missing = []
    for run in sorted(reports):
        try:
            if access.visible(run, source_id=source_id, query=query):
                continue
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            receipt["visibility_errors"][run.label] = type(exc).__name__
        missing.append(run.label)
    receipt["missing_reports"] = missing
    if not missing:
        receipt["publication_status"] = "verified"
    _save(output, receipt)
    return int(bool(missing))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    run = actions.add_parser("run", help="Launch a pipeline or workflow attempt")
    run.add_argument("kind", choices=("pipeline", "workflow"))
    run.add_argument("owner")
    run.add_argument("--mode", choices=("isolated", "publish"), required=True)
    run.add_argument("--data-root", type=Path, required=True)
    retry = actions.add_parser(
        "publish", help="Retry publication without launching BioETL"
    )
    for action in (run, retry):
        action.add_argument("--output", type=Path, required=True)
        action.add_argument("--ops-url", default="http://127.0.0.1:8000")
        action.add_argument("--grafana-url", default="http://127.0.0.1:3000")
        action.add_argument("--timeout", type=float, default=60)
    return parser


def _run(
    args: argparse.Namespace, cli_args: list[str], output: Path, receipt: dict
) -> int:
    prefix = ["run", "--pipeline"] if args.kind == "pipeline" else ["workflow", "run"]
    env = {
        **os.environ,
        "BIOETL_DATA_DIR": receipt["data_root"],
        "BIOETL_REPORT_ROOT": str(output / "run-reports"),
        "BIOETL_ARCHIVE_ROOT": str(output / "archive"),
    }
    if receipt.get("runtime_source_id"):
        env.update(
            BIOETL_RUNTIME_SOURCE_ID=receipt["runtime_source_id"],
            BIOETL_DASHBOARD_DATA_ROOT=receipt["dashboard_data_root"],
        )
    cmd = [sys.executable, "-m", "bioetl", *prefix, args.owner, *cli_args]
    output.mkdir(parents=True, exist_ok=False)
    _save(output, receipt)
    result = subprocess.run(cmd, env=env, cwd=REPO_ROOT, check=False)
    receipt.update(
        execution_status="success" if result.returncode == 0 else "failed",
        exit_code=result.returncode,
    )
    _save(output, receipt)
    return result.returncode if result.returncode >= 0 else 1


def _finish_publication(
    output: Path, target: Path, relative: str, access: DashboardAccess, source_id: str
) -> int:
    with FileLock(output / "publication.lock", timeout=0):
        receipt = read_json(output / RECEIPT)
        try:
            active_source, query = access.preflight(target)
            if active_source != source_id:
                raise ValueError("Runtime source identity changed before publication")
            exit_code = _publish(
                output,
                receipt,
                target=target,
                relative_data_root=relative,
                access=access,
                source_id=source_id,
                query=query,
            )
        except (
            OSError,
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as exc:
            receipt.update(publication_status="failed", publication_error=str(exc))
            _save(output, receipt)
            print(f"Publication failed. See {output / RECEIPT}", file=sys.stderr)
            return 1
    print(f"{receipt['publication_status']}: {output / RECEIPT}")
    return exit_code


def _run_command(argv: list[str] | None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    delimiter = argv.index("--") if "--" in argv else len(argv)
    cli_args = argv[delimiter + 1 :]
    parser = _parser()
    args = parser.parse_args(argv[:delimiter])
    if (args.action == "publish" and cli_args) or not 0 < args.timeout <= 300:
        parser.error("Retry accepts no BioETL arguments; timeout must be in (0, 300]")
    output = _inside(args.output, REPO_ROOT)
    _load_repo_environment()
    mount = Path(
        os.environ.get("BIOETL_DASHBOARD_REPORT_ROOT") or REPO_ROOT / "reports"
    )
    target = _inside(mount / "run-reports", REPO_ROOT)
    alias = _inside(
        Path(os.environ.get("BIOETL_DASHBOARD_DATA_ROOT") or REPO_ROOT / "data"),
        REPO_ROOT,
    )
    access = DashboardAccess(args.ops_url, args.grafana_url, args.timeout)
    if args.action == "run":
        data_root = _inside(args.data_root, REPO_ROOT)
        if (
            not data_root.is_dir()
            or data_root == alias
            or data_root == REPO_ROOT / "data"
        ):
            raise ValueError("Use a prepared, isolated campaign data directory")
        if output.is_relative_to(data_root) or data_root.is_relative_to(output):
            raise ValueError("Attempt output and campaign data roots must be disjoint")
        receipt = {
            "mode": args.mode,
            "kind": args.kind,
            "owner": args.owner,
            "data_root": str(data_root),
            "execution_status": "running",
            "publication_status": "not_requested"
            if args.mode == "isolated"
            else "pending",
        }
    else:
        receipt = read_json(output / RECEIPT)
        if (
            receipt.get("mode") != "publish"
            or receipt.get("execution_status") != "success"
        ):
            raise ValueError(
                "Retry requires a successful attempt started in publish mode"
            )
        data_root = _inside(Path(receipt["data_root"]), REPO_ROOT)
    if output.is_relative_to(target) or target.is_relative_to(output):
        raise ValueError("Attempt output and dashboard report roots must be disjoint")
    if args.action == "run" and args.mode == "isolated":
        return _run(args, cli_args, output, receipt)
    relative = _inside(data_root, alias).relative_to(alias).as_posix()
    source_id, _ = access.preflight(target)
    binding = {
        "runtime_source_id": source_id,
        "dashboard_data_root": str(alias),
        "dashboard_report_root": str(target),
    }
    if args.action == "run":
        receipt.update(binding)
        exit_code = _run(args, cli_args, output, receipt)
        if exit_code:
            return exit_code
    elif any(receipt.get(key) != value for key, value in binding.items()):
        raise ValueError(
            "Publication target or runtime source changed since the attempt"
        )
    return _finish_publication(output, target, relative, access, source_id)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the canonical scripts.ops router."""
    try:
        return _run_command(argv)
    except (OSError, ValueError, KeyError) as error:
        print(f"Campaign setup failed: {error}", file=sys.stderr)
        return 1
