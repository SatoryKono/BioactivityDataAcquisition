"""Run the generated-evidence scheduling contract without masking pytest errors."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("ci", "daily", "validators", "defer-validator")
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--validator")
    args, pytest_args = parser.parse_known_args(argv)
    if pytest_args[:1] == ["--"]:
        pytest_args.pop(0)
    if args.mode in {"validators", "defer-validator"} and pytest_args:
        parser.error("Unexpected arguments for validator operation")
    manifest = load_manifest()
    selectors = {row["node"] for row in manifest["tests"]}
    if args.mode == "defer-validator":
        rows = [row for row in manifest["validators"] if row["id"] == args.validator]
        if len(rows) != 1:
            parser.error("Unknown daily validator; refusing unproven deferral")
        announce(
            f"deferred-to-daily: {args.validator}; owner .github/workflows/nightly.yml (03:00 UTC). No validation PASS is claimed."
        )
        return 0
    if args.mode == "validators":
        outcomes = []
        for row in manifest["validators"]:
            if row["owner"] != "generated-artifact-daily":
                continue
            result = subprocess.run(
                [sys.executable, *row["argv"]], cwd=ROOT, check=False
            )
            outcomes.append(
                {"id": row["id"], "argv": row["argv"], "exit_code": result.returncode}
            )
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(outcomes, indent=2) + "\n", encoding="utf-8"
            )
        return int(any(row["exit_code"] != 0 for row in outcomes))
    if args.report is None:
        parser.error("--report is required for a source-bound partition result")
    # Never consume a previous invocation's proof after a startup/collection error.
    args.report.unlink(missing_ok=True)
    if args.mode == "daily":
        if pytest_args:
            parser.error(
                "Daily selection cannot be narrowed by additional pytest filters"
            )
        pytest_args = sorted({node.split("::", 1)[0] for node in selectors})
        pytest_args += ["-n", "0", "-q", "--tb=short"]
    elif not pytest_args:
        parser.error("CI mode requires explicit affected targets")
    command = [
        sys.executable,
        "-m",
        "pytest",
        *pytest_args,
        f"--artifact-selection={args.mode}",
        f"--artifact-selection-report={args.report}",
    ]
    code = subprocess.run(command, cwd=ROOT, check=False).returncode
    if args.mode == "ci" and code == 5 and args.report.is_file():
        payload = json.loads(args.report.read_text(encoding="utf-8"))
        if proven_deferral(payload, code, selectors):
            announce(
                f"deferred-to-daily: all {len(payload['collected'])} affected nodes are owned by {manifest['daily_workflow']}; pytest exit 5 retained in {args.report}. No tests passed."
            )
            return 0
    return code


if __name__ == "__main__":
    raise SystemExit(main())
