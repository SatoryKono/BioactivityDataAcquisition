#!/usr/bin/env python3
"""Generate a deterministic observed-value inventory for non-ChEMBL normalization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from scripts.engineering.qa.extract_publication_nested_vocab import (
    extract_publication_nested_vocab,
)
from scripts.engineering.qa.extract_pubchem_property_vocab import (
    extract_pubchem_property_vocab,
)
from scripts.engineering.qa.extract_uniprot_semantic_payload_vocab import (
    extract_uniprot_semantic_payload_vocab,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = PROJECT_ROOT / "docs" / "reports" / "generated"
DEFAULT_JSON_OUT = DEFAULT_OUT_DIR / "non_chembl_observed_value_inventory.json"
DEFAULT_MD_OUT = DEFAULT_OUT_DIR / "non_chembl_observed_value_inventory.md"
OBSERVED_FIXTURE_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "normalization" / "non_chembl_observed_values.yaml"
)

_OPENALEX_PATHS = [
    PROJECT_ROOT
    / "tests/fixtures/bronze/openalex/publication/sample_ci_2026-04-29.jsonl",
    PROJECT_ROOT
    / "tests/fixtures/bronze/openalex/publication/sample_edge_nested_vocab_2026-05-05.jsonl",
]
_SEMANTICSCHOLAR_PATHS = [
    PROJECT_ROOT
    / "tests/fixtures/bronze/semanticscholar/publication/sample_ci_2026-04-30.jsonl",
    PROJECT_ROOT
    / "tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl",
]
_PUBMED_PATHS = [
    PROJECT_ROOT
    / "tests/fixtures/bronze/pubmed/publication/sample_edge_publication_types_mesh_2026-05-05.jsonl",
]
_UNIPROT_PATHS = [
    PROJECT_ROOT / "tests/fixtures/bronze/uniprot/protein/sample_ci_2026-04-24.jsonl",
    PROJECT_ROOT
    / "tests/fixtures/bronze/uniprot/protein/sample_edge_semantic_payloads_2026-05-12.jsonl",
]
_PUBCHEM_PATHS = [
    PROJECT_ROOT / "tests/fixtures/bronze/pubchem/compound/sample_ci_2026-04-24.jsonl"
]


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _relative_posix_path(path: Path) -> str:
    """Render repo-relative paths with stable POSIX separators across OSes."""
    return path.relative_to(PROJECT_ROOT).as_posix()


def build_inventory_payload() -> dict[str, object]:
    observed = _load_yaml(OBSERVED_FIXTURE_PATH)["pipelines"]
    publication_vocab = extract_publication_nested_vocab(
        openalex_paths=_OPENALEX_PATHS,
        semanticscholar_paths=_SEMANTICSCHOLAR_PATHS,
        pubmed_paths=_PUBMED_PATHS,
    )
    uniprot_vocab = extract_uniprot_semantic_payload_vocab(_UNIPROT_PATHS)
    pubchem_vocab = extract_pubchem_property_vocab(_PUBCHEM_PATHS)

    return {
        "source": "tracked_non_chembl_bronze_fixtures_and_vcr_derived_edge_samples",
        "observed_fixture_path": _relative_posix_path(OBSERVED_FIXTURE_PATH),
        "sections": {
            "publication_nested_vocab": publication_vocab,
            "crossref_publication_types": sorted(
                observed["crossref_publication"]["observed_values"]["publication_type"]
            ),
            "uniprot_semantic_payloads": uniprot_vocab,
            "uniprot_idmapping": {
                "mapping_status": sorted(
                    observed["uniprot_idmapping"]["observed_values"]["mapping_status"]
                ),
                "all_mappings_expected_normalized": sorted(
                    observed["uniprot_idmapping"]["expected_normalized_values"][
                        "all_mappings"
                    ]
                ),
            },
            "pubchem_property_vocab": pubchem_vocab,
        },
        "fixture_inputs": {
            "openalex": [_relative_posix_path(path) for path in _OPENALEX_PATHS],
            "semanticscholar": [
                _relative_posix_path(path) for path in _SEMANTICSCHOLAR_PATHS
            ],
            "pubmed": [_relative_posix_path(path) for path in _PUBMED_PATHS],
            "uniprot": [_relative_posix_path(path) for path in _UNIPROT_PATHS],
            "pubchem": [_relative_posix_path(path) for path in _PUBCHEM_PATHS],
        },
    }


def _render_markdown(payload: dict[str, object]) -> str:
    sections = payload["sections"]
    assert isinstance(sections, dict)
    lines = [
        "# Non-ChEMBL Observed Value Inventory",
        "",
        f"- source: `{payload['source']}`",
        f"- observed_fixture_path: `{payload['observed_fixture_path']}`",
        "",
        "## Sections",
        "",
    ]
    for section_name, section_payload in sections.items():
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(section_payload, ensure_ascii=False, sort_keys=True, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether generated outputs already match the repo-backed artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    payload = build_inventory_payload()
    markdown = _render_markdown(payload)
    rendered_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if args.check:
        failures: list[str] = []
        if not args.json_out.exists() or args.json_out.read_text(encoding="utf-8") != rendered_json:
            failures.append(str(args.json_out))
        if not args.markdown_out.exists() or args.markdown_out.read_text(encoding="utf-8") != markdown:
            failures.append(str(args.markdown_out))
        if failures:
            print(
                "Non-ChEMBL observed value inventory is stale. Re-run the report generator.",
                file=sys.stderr,
            )
            for failure in failures:
                print(f" - {failure}", file=sys.stderr)
            return 1
        return 0

    _write_json(args.json_out, payload)
    _write_text(args.markdown_out, markdown)
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.markdown_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
