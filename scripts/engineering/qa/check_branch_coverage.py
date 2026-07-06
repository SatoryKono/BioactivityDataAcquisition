"""Enforce the repo-wide branch coverage threshold from Cobertura XML."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COVERAGE_XML = PROJECT_ROOT / "reports" / "coverage" / "coverage.xml"
DEFAULT_MIN_PERCENT = 85.0


@dataclass(frozen=True, slots=True)
class BranchCoverageResult:
    """Branch coverage gate evaluation result."""

    status: str
    coverage_xml: str
    branch_rate_percent: float
    branch_covered: int
    branch_total: int
    required_branch_covered: int
    threshold_percent: float
    threshold_margin: int


def _parse_non_negative_int(value: str | None, *, field: str) -> int:
    if value is None:
        raise ValueError(f"coverage XML is missing {field!r}")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"coverage XML has invalid {field!r}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"coverage XML has negative {field!r}: {parsed}")
    return parsed


def evaluate_branch_coverage(
    coverage_xml: Path,
    *,
    min_percent: float = DEFAULT_MIN_PERCENT,
    repo_root: Path = PROJECT_ROOT,
) -> BranchCoverageResult:
    """Evaluate branch coverage against ``min_percent`` using branch counts."""

    if not coverage_xml.exists():
        raise FileNotFoundError(f"missing coverage XML: {coverage_xml}")
    if min_percent < 0 or min_percent > 100:
        raise ValueError("--min-percent must be between 0 and 100")

    root = ElementTree.parse(coverage_xml).getroot()
    branch_total = _parse_non_negative_int(
        root.attrib.get("branches-valid"),
        field="branches-valid",
    )
    branch_covered = _parse_non_negative_int(
        root.attrib.get("branches-covered"),
        field="branches-covered",
    )
    if branch_covered > branch_total:
        raise ValueError("coverage XML has branches-covered greater than branches-valid")
    if branch_total == 0:
        raise ValueError("coverage XML does not contain branch measurement data")

    required = math.ceil(branch_total * (min_percent / 100.0))
    margin = branch_covered - required
    rate_percent = round((branch_covered / branch_total) * 100.0, 3)
    status = "pass" if margin >= 0 else "fail"

    try:
        display_path = coverage_xml.resolve().relative_to(repo_root.resolve())
    except ValueError:
        display_path = coverage_xml

    return BranchCoverageResult(
        status=status,
        coverage_xml=str(display_path).replace("\\", "/"),
        branch_rate_percent=rate_percent,
        branch_covered=branch_covered,
        branch_total=branch_total,
        required_branch_covered=required,
        threshold_percent=float(min_percent),
        threshold_margin=margin,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce branch coverage from reports/coverage/coverage.xml."
    )
    parser.add_argument(
        "--coverage-xml",
        type=Path,
        default=DEFAULT_COVERAGE_XML,
        help="Cobertura coverage XML to inspect.",
    )
    parser.add_argument(
        "--min-percent",
        type=float,
        default=DEFAULT_MIN_PERCENT,
        help="Minimum branch coverage percent.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional JSON evidence artifact path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = evaluate_branch_coverage(
            args.coverage_xml,
            min_percent=args.min_percent,
        )
    except (FileNotFoundError, OSError, ElementTree.ParseError, ValueError) as exc:
        print(f"[branch-coverage] error: {exc}")
        return 2

    payload = asdict(result)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")

    print(
        "[branch-coverage] "
        f"{result.status}: {result.branch_rate_percent:.3f}% "
        f"({result.branch_covered}/{result.branch_total}); "
        f"threshold={result.threshold_percent:g}%; "
        f"margin={result.threshold_margin}"
    )
    return 0 if result.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
