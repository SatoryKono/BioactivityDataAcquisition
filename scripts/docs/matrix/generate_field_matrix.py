#!/usr/bin/env python3
"""Generate deterministic ChemBL Activity field-matrix artifacts from code."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import ensure_repo_imports

ensure_repo_imports(include_src=True)

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.infrastructure.schemas.silver_chembl_core import (
    CHEMBL_ACTIVITY_SCHEMA,
)

DEFAULT_OUT_DIR = Path("docs/reports/generated/chembl_activity_field_matrix")
CSV_NAME = "chembl_activity_field_matrix.csv"
MD_NAME = "chembl_activity_field_matrix.md"
DOCX_NAME = "chembl_activity_field_matrix.docx"
PDF_NAME = "chembl_activity_field_matrix.pdf"

CSV_COLUMNS = (
    "field_name",
    "type",
    "category",
    "current_normalization",
    "proposed_normalization",
    "include_in_content_hash",
    "set_like",
    "normalizer",
    "notes",
)

_PROPOSED_NORMALIZATION_OVERRIDES: dict[str, str] = {}


def _normalizer_name(normalizer: Any) -> str:
    """Return a deterministic display name for one field normalizer."""
    return getattr(normalizer, "__name__", type(normalizer).__name__)


def _current_normalization_name(*, field_name: str, normalizer_name: str) -> str:
    """Return the display name used by the shipped field-matrix contract."""
    if (
        field_name == "activity_properties"
        and normalizer_name
        in {"normalize_profile_json_string", "normalize_profile_json_string_strict"}
    ):
        return "_normalize_json_string"
    return normalizer_name


def _render_current_normalization(
    *, normalizer_name: str, include_in_hash: bool, set_like: bool
) -> str:
    """Render the active normalization contract from one field rule."""
    parts = [f"normalizer={normalizer_name}"]
    parts.append("content_hash=included" if include_in_hash else "content_hash=excluded")
    if set_like:
        parts.append("hash_order=set_like")
    return "; ".join(parts)


def _render_proposed_normalization(
    field_name: str, current_normalization: str
) -> str:
    """Render planned normalization contract with deterministic fallback."""
    return _PROPOSED_NORMALIZATION_OVERRIDES.get(field_name, current_normalization)


def build_field_matrix_rows() -> list[dict[str, str]]:
    """Build one deterministic field matrix from the canonical schema + profile."""
    schema_fields = tuple(CHEMBL_ACTIVITY_SCHEMA.names)
    profile_fields = tuple(sorted(CHEMBL_ACTIVITY_SCHEMA_FIELDS))
    if tuple(sorted(schema_fields)) != profile_fields:
        raise ValueError("CHEMBL_ACTIVITY_SCHEMA and profile fields are out of sync")
    rows: list[dict[str, str]] = []
    for field_name in sorted(schema_fields):
        rule = CHEMBL_ACTIVITY_PROFILE.rule_for(field_name)
        if rule is None:
            raise ValueError(f"Missing profile rule for {field_name}")
        field = CHEMBL_ACTIVITY_SCHEMA.field(field_name)
        normalizer_name = _normalizer_name(rule.normalizer)
        current_normalization = _render_current_normalization(
            normalizer_name=_current_normalization_name(
                field_name=field_name,
                normalizer_name=normalizer_name,
            ),
            include_in_hash=rule.include_in_hash,
            set_like=rule.set_like,
        )
        rows.append(
            {
                "field_name": field_name,
                "type": str(field.type),
                "category": (
                    "meta"
                    if field_name in CHEMBL_ACTIVITY_PROFILE.meta_fields
                    else "business"
                ),
                "current_normalization": current_normalization,
                "proposed_normalization": _render_proposed_normalization(
                    field_name,
                    current_normalization,
                ),
                "include_in_content_hash": "true" if rule.include_in_hash else "false",
                "set_like": "true" if rule.set_like else "false",
                "normalizer": normalizer_name,
                "notes": rule.notes or "",
            }
        )
    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    """Render one deterministic CSV payload."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(CSV_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_markdown(rows: list[dict[str, str]]) -> str:
    """Render one deterministic Markdown table."""
    headers = list(rows[0].keys())
    lines = [
        "# ChemBL Activity Field Matrix",
        "",
        "Generated from `ActivitySchema` and `CHEMBL_ACTIVITY_PROFILE`.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[header] for header in headers) + " |")
    lines.append("")
    return "\n".join(lines)


def build_artifacts() -> dict[str, str]:
    """Build in-memory text artifacts for CSV and Markdown outputs."""
    rows = build_field_matrix_rows()
    return {
        CSV_NAME: render_csv(rows),
        MD_NAME: render_markdown(rows),
    }


def _write_optional_docx(path: Path, markdown_payload: str) -> str | None:
    try:
        from docx import Document  # type: ignore[import-not-found]
    except ImportError:
        return "python-docx not installed; skipped DOCX export"
    document = Document()
    for line in markdown_payload.splitlines():
        document.add_paragraph(line)
    document.save(path)
    return None


def _write_optional_pdf(path: Path, markdown_payload: str) -> str | None:
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
        from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
    except ImportError:
        return "reportlab not installed; skipped PDF export"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for line in markdown_payload.splitlines():
        pdf.drawString(40, y, line[:120])
        y -= 14
        if y < 40:
            pdf.showPage()
            y = 800
    pdf.save()
    return None


def write_artifacts(
    out_dir: Path,
    *,
    with_docx: bool,
    with_pdf: bool,
) -> dict[str, Any]:
    """Write field-matrix artifacts to one output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        (out_dir / name).write_text(payload, encoding="utf-8")

    warnings: list[str] = []
    if with_docx:
        warning = _write_optional_docx(out_dir / DOCX_NAME, artifacts[MD_NAME])
        if warning is not None:
            warnings.append(warning)
    if with_pdf:
        warning = _write_optional_pdf(out_dir / PDF_NAME, artifacts[MD_NAME])
        if warning is not None:
            warnings.append(warning)
    return {
        "out_dir": str(out_dir),
        "rows": len(build_field_matrix_rows()),
        "warnings": warnings,
    }


def check_artifacts(out_dir: Path) -> int:
    """Return 0 when generated text artifacts already match disk."""
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        path = out_dir / name
        if not path.exists():
            return 1
        if path.read_text(encoding="utf-8") != payload:
            return 1
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic ChemBL Activity field-matrix artifacts from code."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for generated artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 when artifacts on disk differ from the generated output.",
    )
    parser.add_argument(
        "--with-docx",
        action="store_true",
        help="Attempt DOCX export; gracefully skips when dependency is unavailable.",
    )
    parser.add_argument(
        "--with-pdf",
        action="store_true",
        help="Attempt PDF export; gracefully skips when dependency is unavailable.",
    )
    return parser


def main() -> int:
    args = _arg_parser().parse_args()
    out_dir = args.out_dir.resolve()
    if args.check:
        return check_artifacts(out_dir)
    result = write_artifacts(
        out_dir,
        with_docx=args.with_docx,
        with_pdf=args.with_pdf,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
