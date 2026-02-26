#!/usr/bin/env python3
"""
Render Mermaid diagrams to PNG.

This script provides multiple rendering methods:
1. mermaid-cli (mmdc) - Recommended, requires npm installation
2. mermaid.ink API - Online service, no installation required

Usage:
    python render_diagrams.py                    # Render all diagrams
    python render_diagrams.py --method mmdc     # Use mermaid-cli
    python render_diagrams.py --method api      # Use mermaid.ink API
    python render_diagrams.py -f 01-*.mermaid   # Render specific files
"""

import argparse
import base64
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Default paths relative to project root
DIAGRAMS_BASE = Path("docs/02-architecture/diagrams")
MERMAID_DIR = DIAGRAMS_BASE / "mermaid"
PNG_DIR = DIAGRAMS_BASE / "png"
THEME_CONFIG = Path("docs/02-architecture/mmd-diagrams/theme/mermaid-config.json")
THEME_CSS = Path("docs/02-architecture/mmd-diagrams/theme/custom.css")


def _find_mmdc() -> str | None:
    """Find mmdc executable, handling Windows .cmd wrappers."""
    path = shutil.which("mmdc")
    if path:
        return path
    # Fallback: common npm global location on Windows
    if sys.platform == "win32":
        cmd_path = Path.home() / "AppData/Roaming/npm/mmdc.cmd"
        if cmd_path.exists():
            return str(cmd_path)
    return None


def render_with_mmdc(
    input_path: Path,
    output_path: Path,
    width: int = 2400,
    height: int = 1800,
    scale: int = 3,
    *,
    mmdc_path: str = "mmdc",
    config_path: Path | None = None,
    css_path: Path | None = None,
) -> bool:
    """Render using mermaid-cli (mmdc)."""
    try:
        cmd = [
            mmdc_path,
            "-i",
            str(input_path),
            "-o",
            str(output_path),
            "-w",
            str(width),
            "-H",
            str(height),
            "-s",
            str(scale),
            "-b",
            "white",
        ]
        if config_path is not None and config_path.exists():
            cmd.extend(["-c", str(config_path)])
        if css_path is not None and css_path.exists():
            cmd.extend(["--cssFile", str(css_path)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=(sys.platform == "win32"),
        )
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        print(
            "  Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
        )
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


def check_mmdc_available() -> str | None:
    """Check if mmdc is available. Returns the path or None."""
    mmdc = _find_mmdc()
    if not mmdc:
        return None
    try:
        result = subprocess.run(
            [mmdc, "--version"],
            capture_output=True,
            timeout=5,
            shell=(sys.platform == "win32"),
        )
        return mmdc if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams to PNG")
    parser.add_argument(
        "--method",
        choices=["mmdc", "api", "auto"],
        default="auto",
        help="Rendering method (default: auto)",
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        help="Specific files to render (glob patterns supported)",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=2400,
        help="Output width in pixels (default: 2400)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1800,
        help="Output height in pixels (default: 1800)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=3,
        help="Scale factor for mmdc (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Output directory (default: {PNG_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API requests (default: 0.5s)",
    )
    args = parser.parse_args()

    # Find diagram directory
    mermaid_dir = MERMAID_DIR
    if not mermaid_dir.exists():
        # Try relative to script location
        mermaid_dir = Path(__file__).resolve().parent.parent / MERMAID_DIR
    if not mermaid_dir.exists():
        print(f"Mermaid directory not found: {MERMAID_DIR}")
        sys.exit(1)

    # Output directory
    output_dir = args.output_dir or PNG_DIR
    if not output_dir.exists():
        # Try relative to script location
        alt = Path(__file__).resolve().parent.parent / output_dir
        if alt.exists():
            output_dir = alt
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find mermaid files
    if args.files:
        mermaid_files = []
        for pattern in args.files:
            mermaid_files.extend(mermaid_dir.glob(pattern))
        mermaid_files = sorted(mermaid_files)
    else:
        mermaid_files = sorted(mermaid_dir.glob("*.mermaid"))

    if not mermaid_files:
        print(f"No mermaid files found in {mermaid_dir}")
        sys.exit(0)

    print(f"Found {len(mermaid_files)} mermaid file(s)")
    print(f"  Source: {mermaid_dir}")
    print(f"  Output: {output_dir}")
    if THEME_CONFIG.exists():
        print(f"  Theme config: {THEME_CONFIG}")
    if THEME_CSS.exists():
        print(f"  Theme CSS: {THEME_CSS}")

    # Determine rendering method
    method = args.method
    mmdc_path = "mmdc"
    if method == "auto":
        found = check_mmdc_available()
        if found:
            method = "mmdc"
            mmdc_path = found
            print(f"Using mermaid-cli ({found})")
        else:
            method = "api"
            print("Using mermaid.ink API (mmdc not available)")
    elif method == "mmdc":
        found = check_mmdc_available()
        if found:
            mmdc_path = found
        else:
            print(
                "Error: mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli"
            )
            sys.exit(1)

    # Render each file
    success_count = 0
    for i, mf in enumerate(mermaid_files, 1):
        output_path = output_dir / mf.with_suffix(".png").name
        print(f"[{i}/{len(mermaid_files)}] Rendering {mf.name}...", end=" ", flush=True)

        if method == "mmdc":
            success = render_with_mmdc(
                mf,
                output_path,
                args.width,
                args.height,
                args.scale,
                mmdc_path=mmdc_path,
                config_path=THEME_CONFIG,
                css_path=THEME_CSS,
            )
        else:
            success = render_with_api(mf, output_path)
            time.sleep(args.delay)  # Rate limiting

        if success:
            size = output_path.stat().st_size
            print(f"OK ({size:,} bytes)")
            success_count += 1
        else:
            print("FAILED")

    print(f"\nRendered {success_count}/{len(mermaid_files)} diagrams")
    sys.exit(0 if success_count == len(mermaid_files) else 1)


if __name__ == "__main__":
    main()
