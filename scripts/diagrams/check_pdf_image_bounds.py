#!/usr/bin/env python3
"""Validate that embedded PDF images fit inside page bounds."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz


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


def validate_pdf(pdf_path: Path, max_overflow_ratio: float) -> list[BoundsIssue]:
    issues: list[BoundsIssue] = []
    doc = fitz.open(str(pdf_path))

    page_count = getattr(doc, "page_count", None) or getattr(doc, "pageCount", 0)
    for page_idx in range(page_count):
        page = (
            doc.load_page(page_idx)
            if hasattr(doc, "load_page")
            else doc.loadPage(page_idx)
        )
        rect = page.rect
        page_width = float(rect.width)
        page_height = float(rect.height)
        content = (
            page.get_text("dict") if hasattr(page, "get_text") else page.getText("dict")
        )
        image_blocks = [b for b in content.get("blocks", []) if b.get("type") == 1]

        for image_idx, block in enumerate(image_blocks, start=1):
            bbox_raw = block.get("bbox", [0.0, 0.0, 0.0, 0.0])
            x0, y0, x1, y1 = (float(v) for v in bbox_raw)
            bbox_width = x1 - x0
            bbox_height = y1 - y0
            img_width = int(block.get("width", 0))
            img_height = int(block.get("height", 0))

            if x0 < 0 or y0 < 0 or x1 > page_width or y1 > page_height:
                issues.append(
                    BoundsIssue(
                        page=page_idx + 1,
                        image_index=image_idx,
                        bbox=[x0, y0, x1, y1],
                        page_size=[page_width, page_height],
                        image_size=[img_width, img_height],
                        kind="PDF-BOUNDS-001",
                        message="Image bbox exceeds page area (likely clipping).",
                    )
                )
                continue

            if bbox_width > page_width * max_overflow_ratio:
                issues.append(
                    BoundsIssue(
                        page=page_idx + 1,
                        image_index=image_idx,
                        bbox=[x0, y0, x1, y1],
                        page_size=[page_width, page_height],
                        image_size=[img_width, img_height],
                        kind="PDF-BOUNDS-002",
                        message=(
                            "Image bbox width exceeds page width threshold "
                            f"({bbox_width:.2f} > {page_width * max_overflow_ratio:.2f})."
                        ),
                    )
                )

            if bbox_height > page_height * max_overflow_ratio:
                issues.append(
                    BoundsIssue(
                        page=page_idx + 1,
                        image_index=image_idx,
                        bbox=[x0, y0, x1, y1],
                        page_size=[page_width, page_height],
                        image_size=[img_width, img_height],
                        kind="PDF-BOUNDS-003",
                        message=(
                            "Image bbox height exceeds page height threshold "
                            f"({bbox_height:.2f} > {page_height * max_overflow_ratio:.2f})."
                        ),
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
