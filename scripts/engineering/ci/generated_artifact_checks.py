"""Run the generated-evidence scheduling contract without masking pytest errors."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.engineering.common.repo_paths import ensure_safe_cli_argv
from scripts.engineering.dev.pytest_artifact_selection import (
    MANIFEST,
    ROOT,
    base_node,
    load_manifest,
)


def proven_deferral(payload: dict, exit_code: int, selectors: set[str]) -> bool:
    """Accept only an entirely collected, explicitly owned artifact selection."""
    collected = payload.get("collected")
    return bool(
        exit_code == 5
        and payload.get("pytest_exit_code") == 5
        and payload.get("status") == "deferred-to-daily"
        and payload.get("selection") == "ci"
        and payload.get("collection_errors") == 0
        and isinstance(collected, list)
        and collected
        and not payload.get("selected")
        and not payload.get("other_deselected")
        and collected == payload.get("deferred")
        and all(
            isinstance(node, str) and base_node(node) in selectors for node in collected
        )
    )


def announce(message: str) -> None:
    print(message, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


REPORT_NAMES = {
    "ci": "affected-test-partition.json",
    "daily": "generated-artifact-daily-selection.json",
    "validators": "generated-artifact-daily-validators.json",
}


def report_destination(mode: str, supplied: Path | None) -> Path | None:
    """Accept only the mode's fixed report, never a caller-chosen deletion target."""
    if supplied is None:
        if mode in {"ci", "daily"}:
            raise ValueError("--report is required")
        return None
    if mode not in REPORT_NAMES or ".." in supplied.parts:
        raise ValueError("Invalid report destination")
    root = ROOT.resolve()
    expected = root / "reports" / "quality" / REPORT_NAMES[mode]
    candidate = supplied if supplied.is_absolute() else root / supplied
    if candidate != expected:
        raise ValueError(f"Report must be {expected.relative_to(root)}")
    _reject_symlinks(expected, root)
    if expected.exists() and not expected.is_file():
        raise ValueError("Report destination must be a regular file")
    return expected


def _reject_symlinks(path: Path, root: Path) -> None:
    """Reject symlink components, including dangling links, before filesystem IO."""
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink path is not allowed: {current}")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escapes repository")


def traceback_option(value: str) -> str:
    """Emit only literal pytest options, even when parser validation is bypassed."""
    options = {
        "line": "--tb=line",
        "short": "--tb=short",
        "long": "--tb=long",
        "auto": "--tb=auto",
        "native": "--tb=native",
        "no": "--tb=no",
    }
    try:
        return options[value]
    except KeyError as exc:
        raise ValueError("Unsupported pytest traceback format") from exc


def ci_pytest_arguments(argv: list[str]) -> list[str]:
    """Parse a narrow pytest interface and terminate options before test targets."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("-q", action="store_true")
    parser.add_argument(
        "--tb",
        choices=("line", "short", "long", "auto", "native", "no"),
        default="short",
    )
    parser.add_argument("targets", nargs="+")
    args = parser.parse_args(argv)
    targets = []
    root = ROOT.resolve()
    for target in args.targets:
        file_part = target.split("::", 1)[0]
        path = Path(file_part)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "tests"
        ):
            raise ValueError("Targets must be repository-relative paths under tests/")
        if any(ord(char) < 32 for char in target):
            raise ValueError("Control characters are not allowed in targets")
        # Reject before symlink or existence probes. Names containing |, > or <
        # are illegal on Windows, so the check must not touch the filesystem.
        ensure_safe_cli_argv([target])
        _reject_symlinks(root / path, root)
        if not (root / path).exists():
            raise ValueError(f"Test target does not exist: {file_part}")
        targets.append(target)
    return ensure_safe_cli_argv(
        (["-q"] if args.q else []) + [traceback_option(args.tb), "--", *targets]
    )


def _pytest_command(mode: str, pytest_args: list[str]) -> list[str]:
    """Build pytest argv from fixed mode tokens and reject shell metacharacters."""
    if mode == "ci":
        selection = "--artifact-selection=ci"
        report_name = REPORT_NAMES["ci"]
    elif mode == "daily":
        selection = "--artifact-selection=daily"
        report_name = REPORT_NAMES["daily"]
    else:
        raise ValueError("Only CI and daily modes run pytest")
    report_arg = (
        "--artifact-selection-report="
        + (ROOT / "reports" / "quality" / report_name).as_posix()
    )
    return ensure_safe_cli_argv(
        [sys.executable, "-m", "pytest", selection, report_arg, *pytest_args]
    )


def _parse_arguments(argv: list[str] | None):
    raw = list(sys.argv[1:] if argv is None else argv)
    split = raw.index("--") if "--" in raw else len(raw)
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "mode", choices=("ci", "daily", "validators", "defer-validator")
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--validator")
    args = parser.parse_args(raw[:split])
    tail = raw[split + 1 :]
    try:
        report = report_destination(args.mode, args.report)
        if args.mode != "ci" and tail:
            raise ValueError("Only CI mode accepts explicit pytest targets/options")
        pytest_args = ci_pytest_arguments(tail) if args.mode == "ci" else []
    except ValueError as error:
        parser.error(str(error))
    return args, report, pytest_args


def _run_validators(manifest: dict, report: Path | None) -> int:
    outcomes = []
    for row in manifest["validators"]:
        if row["owner"] == "generated-artifact-daily":
            result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
                ensure_safe_cli_argv([sys.executable, *row["argv"]]),
                cwd=ROOT,
                check=False,
            )
            outcomes.append(
                {"id": row["id"], "argv": row["argv"], "exit_code": result.returncode}
            )
    if report is not None:
        report_destination("validators", report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(outcomes, indent=2) + "\n", encoding="utf-8")
    return int(any(row["exit_code"] != 0 for row in outcomes))


def _run_tests(mode: str, report: Path, pytest_args: list[str], manifest: dict) -> int:
    selectors = {row["node"] for row in manifest["tests"]}
    if mode == "daily":
        pytest_args = [
            "-n",
            "0",
            "-q",
            "--tb=short",
            "--",
            *sorted({node.split("::", 1)[0] for node in selectors}),
        ]
    try:
        command = _pytest_command(mode, pytest_args)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    report_destination(mode, report)
    report.unlink(missing_ok=True)
    code = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        command,
        cwd=ROOT,
        check=False,
    ).returncode
    report_destination(mode, report)
    if mode == "ci" and code == 5 and report.is_file():
        payload = json.loads(report.read_text(encoding="utf-8"))
        if proven_deferral(payload, code, selectors):
            announce(
                f"deferred-to-daily: all {len(payload['collected'])} affected nodes are owned by {manifest['daily_workflow']}; pytest exit 5 retained in {report}. No tests passed."
            )
            return 0
    return code


def main(argv: list[str] | None = None) -> int:
    args, report, pytest_args = _parse_arguments(argv)
    manifest = load_manifest()
    if args.mode == "defer-validator":
        rows = [row for row in manifest["validators"] if row["id"] == args.validator]
        if len(rows) != 1:
            raise SystemExit("Unknown daily validator; refusing unproven deferral")
        announce(
            f"deferred-to-daily: {args.validator}; owner .github/workflows/nightly.yml (03:00 UTC). No validation PASS is claimed."
        )
        return 0
    if args.mode == "validators":
        return _run_validators(manifest, report)
    assert report is not None
    return _run_tests(args.mode, report, pytest_args, manifest)


if __name__ == "__main__":
    raise SystemExit(main())
