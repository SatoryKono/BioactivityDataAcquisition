#!/usr/bin/env python3
"""
Render Mermaid diagrams to PNG.

This script provides multiple rendering methods:
1. mermaid-cli (mmdc) - Recommended, requires npm installation
2. mermaid.ink API - Online service, no installation required
3. Playwright - Headless browser rendering

Usage:
    python render_diagrams.py                    # Render all diagrams
    python render_diagrams.py --method mmdc     # Use mermaid-cli
    python render_diagrams.py --method api      # Use mermaid.ink API
    python render_diagrams.py -f 01-*.mermaid   # Render specific files
"""

import argparse
import base64
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def render_with_mmdc(input_path: Path, output_path: Path, width: int = 1200) -> bool:
    """Render using mermaid-cli (mmdc)."""
    try:
        result = subprocess.run(
            [
                "mmdc",
                "-i", str(input_path),
                "-o", str(output_path),
                "-w", str(width),
                "-b", "transparent",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        print("  Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli")
        return False
    except subprocess.TimeoutExpired:
        print("  Error: Rendering timeout")
        return False


def render_with_api(input_path: Path, output_path: Path) -> bool:
    """Render using mermaid.ink API."""
    try:
        code = input_path.read_text(encoding="utf-8")
        encoded = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/img/base64:{encoded}"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            output_path.write_bytes(response.read())
        return True
    except urllib.error.HTTPError as e:
        print(f"  Error: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def check_mmdc_available() -> bool:
    """Check if mmdc is available."""
    try:
        result = subprocess.run(["mmdc", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main():
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams to PNG")
    parser.add_argument(
        "--method",
        choices=["mmdc", "api", "auto"],
        default="auto",
        help="Rendering method (default: auto)",
    )
    parser.add_argument(
        "-f", "--files",
        nargs="+",
        help="Specific files to render (glob patterns supported)",
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=1200,
        help="Output width in pixels (default: 1200)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API requests (default: 0.5s)",
    )
    args = parser.parse_args()

    # Find diagram directory
    script_dir = Path(__file__).parent
    if not script_dir.exists():
        script_dir = Path("docs/architecture/diagrams")

    # Find mermaid files
    if args.files:
        mermaid_files = []
        for pattern in args.files:
            mermaid_files.extend(script_dir.glob(pattern))
    else:
        mermaid_files = sorted(script_dir.glob("*.mermaid"))

    if not mermaid_files:
        print("No mermaid files found")
        sys.exit(1)

    print(f"Found {len(mermaid_files)} mermaid file(s)")

    # Determine rendering method
    method = args.method
    if method == "auto":
        if check_mmdc_available():
            method = "mmdc"
            print("Using mermaid-cli (mmdc)")
        else:
            method = "api"
            print("Using mermaid.ink API (mmdc not available)")

    # Render each file
    success_count = 0
    for mf in mermaid_files:
        output_path = mf.with_suffix(".png")
        print(f"Rendering {mf.name}...", end=" ", flush=True)

        if method == "mmdc":
            success = render_with_mmdc(mf, output_path, args.width)
        else:
            success = render_with_api(mf, output_path)
            if method == "api":
                time.sleep(args.delay)  # Rate limiting

        if success:
            size = output_path.stat().st_size
            print(f"✓ ({size:,} bytes)")
            success_count += 1
        else:
            print("✗")

    print(f"\nRendered {success_count}/{len(mermaid_files)} diagrams")
    sys.exit(0 if success_count == len(mermaid_files) else 1)


if __name__ == "__main__":
    main()
