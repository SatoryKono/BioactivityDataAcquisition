#!/usr/bin/env python3
"""Validate that embedded PDF images fit inside page bounds."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import fitz  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional PyMuPDF
    fitz = None  # type: ignore[assignment]


@dataclass(frozen=True)
class BoundsIssue:
    page: int
    image_index: int
    bbox: list[float]
    page_size: list[float]
    image_size: list[int]
    kind: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that PDF images are not clipped or overflowed.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        required=True,
        help="Path to PDF file to validate.",
    )
    parser.add_argument(
        "--max-overflow-ratio",
        type=float,
        default=1.02,
        help="Allowed image bbox growth relative to page dimensions (default: 1.02).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output.",
    )
    return parser.parse_args()


def _load_pdf_page(doc: fitz.Document, page_idx: int) -> fitz.Page:
    return (
        doc.load_page(page_idx) if hasattr(doc, "load_page") else doc.loadPage(page_idx)
    )


def _page_content_dict(page: fitz.Page) -> dict[str, object]:
    return page.get_text("dict") if hasattr(page, "get_text") else page.getText("dict")


def _bounds_issue(
    *,
    page_idx: int,
    image_idx: int,
    bbox: list[float],
    page_size: list[float],
    image_size: list[int],
    kind: str,
    message: str,
) -> BoundsIssue:
    return BoundsIssue(
        page=page_idx + 1,
        image_index=image_idx,
        bbox=bbox,
        page_size=page_size,
        image_size=image_size,
        kind=kind,
        message=message,
    )


def _overflow_issue(
    *,
    page_idx: int,
    image_idx: int,
    bbox: list[float],
    page_size: list[float],
    image_size: list[int],
) -> BoundsIssue:
    return _bounds_issue(
        page_idx=page_idx,
        image_idx=image_idx,
        bbox=bbox,
        page_size=page_size,
        image_size=image_size,
        kind="PDF-BOUNDS-001",
        message="Image bbox exceeds page area (likely clipping).",
    )


def _threshold_issue(
    *,
    page_idx: int,
    image_idx: int,
    bbox: list[float],
    page_size: list[float],
    image_size: list[int],
    axis: str,
    measured: float,
    threshold: float,
) -> BoundsIssue:
    kind = "PDF-BOUNDS-002" if axis == "width" else "PDF-BOUNDS-003"
    return _bounds_issue(
        page_idx=page_idx,
        image_idx=image_idx,
        bbox=bbox,
        page_size=page_size,
        image_size=image_size,
        kind=kind,
        message=(
            f"Image bbox {axis} exceeds page {axis} threshold "
            f"({measured:.2f} > {threshold:.2f})."
        ),
    )


def _bbox_exceeds_page(
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    page_width: float,
    page_height: float,
) -> bool:
    return x0 < 0 or y0 < 0 or x1 > page_width or y1 > page_height


def _issues_for_image_block(
    *,
    page_idx: int,
    image_idx: int,
    block: dict[str, object],
    page_width: float,
    page_height: float,
    max_overflow_ratio: float,
) -> list[BoundsIssue]:
    bbox_raw = block.get("bbox", [0.0, 0.0, 0.0, 0.0])
    x0, y0, x1, y1 = (float(v) for v in bbox_raw)
    bbox = [x0, y0, x1, y1]
    page_size = [page_width, page_height]
    bbox_width = x1 - x0
    bbox_height = y1 - y0
    image_size = [int(block.get("width", 0)), int(block.get("height", 0))]

    if _bbox_exceeds_page(
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        page_width=page_width,
        page_height=page_height,
    ):
        return [
            _overflow_issue(
                page_idx=page_idx,
                image_idx=image_idx,
                bbox=bbox,
                page_size=page_size,
                image_size=image_size,
            )
        ]

    issues: list[BoundsIssue] = []
    width_threshold = page_width * max_overflow_ratio
    if bbox_width > width_threshold:
        issues.append(
            _threshold_issue(
                page_idx=page_idx,
                image_idx=image_idx,
                bbox=bbox,
                page_size=page_size,
                image_size=image_size,
                axis="width",
                measured=bbox_width,
                threshold=width_threshold,
            )
        )
    height_threshold = page_height * max_overflow_ratio
    if bbox_height > height_threshold:
        issues.append(
            _threshold_issue(
                page_idx=page_idx,
                image_idx=image_idx,
                bbox=bbox,
                page_size=page_size,
                image_size=image_size,
                axis="height",
                measured=bbox_height,
                threshold=height_threshold,
            )
        )
    return issues


def validate_pdf(pdf_path: Path, max_overflow_ratio: float) -> list[BoundsIssue]:
    issues: list[BoundsIssue] = []
    doc = fitz.open(str(pdf_path))

    page_count = getattr(doc, "page_count", None) or getattr(doc, "pageCount", 0)
    for page_idx in range(page_count):
        page = _load_pdf_page(doc, page_idx)
        rect = page.rect
        page_width = float(rect.width)
        page_height = float(rect.height)
        content = _page_content_dict(page)
        image_blocks = [b for b in content.get("blocks", []) if b.get("type") == 1]

        for image_idx, block in enumerate(image_blocks, start=1):
            issues.extend(
                _issues_for_image_block(
                    page_idx=page_idx,
                    image_idx=image_idx,
                    block=block,
                    page_width=page_width,
                    page_height=page_height,
                    max_overflow_ratio=max_overflow_ratio,
                )
            )

    return issues


def main() -> int:
    args = parse_args()
    pdf_path = args.pdf if args.pdf.is_absolute() else Path.cwd() / args.pdf

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    issues = validate_pdf(pdf_path, args.max_overflow_ratio)
    if args.json:
        payload = {
            "pdf": str(pdf_path),
            "ok": not issues,
            "issues": [asdict(issue) for issue in issues],
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(f"[INFO] Checked PDF: {pdf_path}")
        if issues:
            print("[ERROR] PDF image bounds check failed:")
            for issue in issues:
                print(
                    f"  - {issue.kind} page={issue.page} img={issue.image_index}: "
                    f"{issue.message}"
                )
        else:
            print("[OK] PDF image bounds check passed.")

    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
