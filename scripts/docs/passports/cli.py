"""CLI for BioETL passport documentation projections."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from pathlib import Path

from .projector import build_all_outputs, check_outputs, write_outputs

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_PATHS = (
    "configs/entities",
    "configs/providers",
    "configs/composites",
    "configs/workflows",
    "configs/contracts",
    "src/bioetl/composition/factories/pipeline",
    "src/bioetl/domain/workflow",
    "src/bioetl/infrastructure/config",
)


def _source_tree_is_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *_SOURCE_PATHS],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not result.stdout.strip()


def _validate_generated(outputs: dict[Path, bytes], output_root: Path) -> None:
    jsonschema = importlib.import_module("jsonschema")
    schema_root = output_root / "schemas"
    if not schema_root.is_dir():
        schema_root = PROJECT_ROOT / "docs/04-reference/passports/schemas"
    pipeline_schema = json.loads(
        (schema_root / "pipeline-passport.schema.json").read_text(encoding="utf-8")
    )
    workflow_schema = json.loads(
        (schema_root / "workflow-passport.schema.json").read_text(encoding="utf-8")
    )
    for path, content in outputs.items():
        if path.suffix != ".json" or "generated" not in path.parts:
            continue
        facts = json.loads(content)
        schema = workflow_schema if facts["kind"] == "workflow" else pipeline_schema
        jsonschema.validate(facts, schema)


def _orphan_outputs(outputs: dict[Path, bytes], output_root: Path) -> list[Path]:
    expected = {path.resolve() for path in outputs}
    actual = {
        path.resolve()
        for group in (
            "generated/pipelines",
            "generated/workflows",
            "pipelines",
            "workflows",
        )
        for path in (output_root / group).glob("*")
        if path.suffix in {".json", ".md"}
    }
    return sorted(actual - expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--configs-root", type=Path, default=Path("configs"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("docs/04-reference/passports")
    )
    parser.add_argument("--source-revision")
    parser.add_argument("--manual-root", type=Path)
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help="Fail when canonical passport source paths have working-tree changes.",
    )
    args = parser.parse_args(argv)
    if args.require_clean_source and not _source_tree_is_clean():
        print("Passport source revision is not clean.")
        return 1
    outputs = build_all_outputs(
        configs_root=args.configs_root,
        output_root=args.output_root,
        source_revision=args.source_revision,
        manual_root=args.manual_root,
    )
    _validate_generated(outputs, args.output_root)
    report = json.loads(outputs[args.output_root / "completeness-report.json"])
    if report["blocking_diagnostics"]:
        print(
            "Passport publication blocked by "
            f"{report['blocking_diagnostics']} diagnostics."
        )
        return 1
    if args.action == "check":
        stale = [*check_outputs(outputs), *_orphan_outputs(outputs, args.output_root)]
        if stale:
            for path in stale:
                print(f"stale: {path.as_posix()}")
            return 1
        print(f"Passport artifacts current: {len(outputs)} files")
        return 0
    write_outputs(outputs)
    print(f"Generated passport artifacts: {len(outputs)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
