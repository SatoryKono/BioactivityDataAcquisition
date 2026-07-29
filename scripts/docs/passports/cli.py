"""CLI for BioETL passport documentation projections."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from .projector import build_all_outputs, check_outputs, write_outputs

PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
        for group in ("generated/pipelines", "generated/workflows", "pipelines", "workflows")
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
    args = parser.parse_args(argv)
    outputs = build_all_outputs(
        configs_root=args.configs_root,
        output_root=args.output_root,
        source_revision=args.source_revision,
        manual_root=args.manual_root,
    )
    _validate_generated(outputs, args.output_root)
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
