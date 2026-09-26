"""Artifact rendering, persistence, and CLI for the normalization matrix."""

from __future__ import annotations

from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    CSV_COLUMNS,
    CSV_NAME,
    ENTITY_PIPELINE_KIND,
    MD_NAME,
    NON_CHEMBL_MD_NAME,
    NON_CHEMBL_PIPELINES,
    Path,
    Sequence,
    _build_arg_parser,
    argparse,
    build_field_matrix_rows,
    build_profile_semantic_invariants,
    build_surface_coverage_kpis,
    csv,
    io,
    yaml,
)

def render_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(CSV_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_markdown(
    rows: list[dict[str, str]],
    *,
    surface_kpis: list[dict[str, object]] | None = None,
    semantic_kpis: list[dict[str, object]] | None = None,
) -> str:
    headers = list(CSV_COLUMNS)
    effective_surface_kpis = (
        build_surface_coverage_kpis(rows) if surface_kpis is None else surface_kpis
    )
    effective_semantic_kpis = (
        build_profile_semantic_invariants() if semantic_kpis is None else semantic_kpis
    )
    lines = _markdown_intro_lines()
    lines.extend(_surface_kpi_lines(effective_surface_kpis))
    lines.extend(_semantic_kpi_lines(effective_semantic_kpis))
    lines.extend(_markdown_table_lines(rows, headers))
    lines.append("")
    return "\n".join(lines)


def _markdown_intro_lines() -> list[str]:
    """Render static markdown prelude for normalization matrix artifacts."""
    return [
        "# Pipeline Normalization Field Matrix",
        "",
        (
            "Generated from active pipeline configs, Silver schemas, domain schema "
            "contracts, DQ policy configs, and current normalization code paths."
        ),
        "",
        "This matrix is a normalization inventory, not a persisted-row publication contract.",
        (
            "Occurrence-scoped provenance fields may appear here because normalization "
            "or config policy still references them,"
        ),
        "but canonical Silver/Gold row contracts are defined by provider references and Gold contract exports.",
        "",
        (
            "Governance columns expose controlled-vocabulary sources, content_hash "
            "scope, content_hash inclusion, hash ordering, semantic category, "
            "strictness, domain/Silver schema visibility, and DQ rule visibility "
            "for each field."
        ),
        "",
        "## Surface Coverage Summary",
        "",
        (
            "Entity coverage is entity-scoped only; composite join-key and "
            "control-plane surfaces are reported separately below."
        ),
        "",
    ]


def _surface_kpi_lines(surface_kpis: list[dict[str, object]]) -> list[str]:
    """Render surface coverage KPI bullet lines."""
    return [
        (
            f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
            f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
        )
        for kpi in surface_kpis
    ]


def _semantic_kpi_lines(semantic_kpis: list[dict[str, object]]) -> list[str]:
    """Render semantic invariant KPI bullet lines."""
    lines = ["", "## Semantic Invariant Summary", ""]
    lines.extend(_semantic_kpi_line(kpi) for kpi in semantic_kpis)
    return lines


def _semantic_kpi_line(kpi: dict[str, object]) -> str:
    """Render one semantic invariant KPI line with optional regressions."""
    regressions_raw = kpi.get("regressions", [])
    regressions = (
        [item for item in regressions_raw if isinstance(item, str)]
        if isinstance(regressions_raw, list)
        else []
    )
    regression_note = f" Regressions: {', '.join(regressions)}." if regressions else ""
    return (
        f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
        f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
        f"{regression_note}"
    )


def _markdown_table_lines(
    rows: list[dict[str, str]],
    headers: Sequence[str],
) -> list[str]:
    """Render markdown table header and all matrix rows."""
    lines = [
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(_markdown_table_row(row, headers) for row in rows)
    return lines


def _markdown_table_row(row: dict[str, str], headers: Sequence[str]) -> str:
    """Render one markdown table row."""
    return "| " + " | ".join(row.get(header, "") for header in headers) + " |"


def build_artifacts(
    rows: list[dict[str, str]] | None = None,
    *,
    surface_kpis: list[dict[str, object]] | None = None,
    semantic_kpis: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    matrix_rows = build_field_matrix_rows() if rows is None else rows
    effective_surface_kpis = (
        build_surface_coverage_kpis(matrix_rows)
        if surface_kpis is None
        else surface_kpis
    )
    effective_semantic_kpis = (
        build_profile_semantic_invariants() if semantic_kpis is None else semantic_kpis
    )
    non_chembl_rows = [
        row
        for row in matrix_rows
        if row["pipeline_kind"] == ENTITY_PIPELINE_KIND
        and row["pipeline_name"] in NON_CHEMBL_PIPELINES
    ]
    return {
        CSV_NAME: render_csv(matrix_rows),
        MD_NAME: render_markdown(
            matrix_rows,
            surface_kpis=effective_surface_kpis,
            semantic_kpis=effective_semantic_kpis,
        ),
        NON_CHEMBL_MD_NAME: render_markdown(
            non_chembl_rows,
            surface_kpis=effective_surface_kpis,
            semantic_kpis=effective_semantic_kpis,
        ),
    }


def _normalize_newlines(payload: str) -> str:
    """Normalize line endings for deterministic cross-platform comparisons."""
    return payload.replace("\r\n", "\n").replace("\r", "\n")


def write_artifacts(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_field_matrix_rows()
    surface_kpis = build_surface_coverage_kpis(rows)
    semantic_kpis = build_profile_semantic_invariants()
    artifacts = build_artifacts(
        rows,
        surface_kpis=surface_kpis,
        semantic_kpis=semantic_kpis,
    )
    for name, payload in artifacts.items():
        (out_dir / name).write_text(payload, encoding="utf-8", newline="\n")
    return {
        "out_dir": str(out_dir),
        "rows": len(rows),
        "coverage_kpi": surface_kpis[0],
        "surface_kpis": surface_kpis,
        "semantic_kpis": semantic_kpis,
    }


def check_artifacts(out_dir: Path) -> int:
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        path = out_dir / name
        if not path.exists():
            return 1
        if _normalize_newlines(path.read_text(encoding="utf-8")) != _normalize_newlines(
            payload
        ):
            return 1
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    return _build_arg_parser()


def main(argv: Sequence[str] | None = None) -> int:
    args = _arg_parser().parse_args(argv)
    out_dir = args.out_dir.resolve()
    if args.check:
        return check_artifacts(out_dir)
    result = write_artifacts(out_dir)
    print(yaml.safe_dump(result, sort_keys=False), end="")
    return 0



