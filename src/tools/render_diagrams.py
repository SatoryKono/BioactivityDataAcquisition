"""CLI tool to render Mermaid diagrams to PNG using mermaid-cli."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Iterable

logger = logging.getLogger(__name__)

MERMAID_CLI_VERSION = "10.9.1"
MERMAID_CLI_PACKAGE = f"@mermaid-js/mermaid-cli@{MERMAID_CLI_VERSION}"

_FRONT_MATTER_PATTERN = re.compile(
    r"^---\s*[\r\n].*?[\r\n]---\s*[\r\n]?", flags=re.DOTALL
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Mermaid (*.mmd) diagrams under root to PNG.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("docs"),
        help="Root directory to search for *.mmd files (default: docs)",
    )
    parser.add_argument(
        "--background",
        default="white",
        help="Background color passed to mermaid-cli (default: white)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=10.0,
        help="Scale factor for mermaid-cli (default: 10.0)",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="default",
        help="Mermaid theme name",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to mermaid config JSON",
    )
    return parser.parse_args()


def _npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def _local_mmdc() -> Path | None:
    base = Path("node_modules") / ".bin"
    for name in ("mmdc.cmd", "mmdc"):
        bin_path = base / name
        if bin_path.exists():
            return bin_path.resolve()
    return None


def _find_chromium_exe() -> Path | None:
    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/bin/chromium"),
                Path("/usr/bin/chromium-browser"),
                Path("/usr/bin/google-chrome"),
                Path("/opt/google/chrome/chrome"),
            ]
        )
    for chromium_path in candidates:
        if chromium_path.exists():
            return chromium_path
    return None


def _strip_front_matter(content: str) -> str:
    match = _FRONT_MATTER_PATTERN.match(content)
    if match is None:
        return content
    return content[match.end() :]


def _sanitize_mermaid(content: str) -> str:
    """Remove style fragments that trigger mermaid-cli parser bugs.

    Some combinations of ``color:#...`` and ``font-size:...`` in ``classDef``
    and ``linkStyle`` definitions cause parse errors on Windows when rendered
    via mermaid-cli 10.9.x.

    We strip these attributes, сохраняя остальную разметку диаграммы.
    """

    def _sanitize_line(line: str) -> str:
        line = re.sub(r",\s*color:#(?:[0-9a-fA-F]{3,6})", "", line)
        line = re.sub(r",\s*font-size:\d+px", "", line)
        return line

    return "\n".join(_sanitize_line(line) for line in content.splitlines())


def _cleanup_temp(root: Path) -> None:
    for pattern in ("*.render.mmd", "*.render.png"):
        for temp_path in root.rglob(pattern):
            if temp_path.is_file():
                temp_path.unlink(missing_ok=True)


def _find_diagrams(root: Path) -> list[Path]:
    diagrams: list[Path] = []
    for path in root.rglob("*.mmd"):
        if not path.is_file():
            continue
        if ".render." in path.name:
            continue
        diagrams.append(path.resolve())
    return sorted(diagrams)


def _render_diagram(
    path: Path,
    background: str,
    scale: float,
    theme: str,
    config: Path | None,
) -> tuple[bool, str]:
    try:
        raw_content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        return False, f"missing input: {exc}"

    content = _sanitize_mermaid(_strip_front_matter(raw_content))

    target = path.with_suffix(".png").resolve()
    base_dir = target.parent
    base_dir.mkdir(parents=True, exist_ok=True)

    tmp_in_path = base_dir / f"{target.stem}.render.mmd"
    tmp_out_path = base_dir / f"{target.stem}.render.png"

    tmp_in_path.write_text(content, encoding="utf-8")

    logger.info("Rendering %s -> %s", path, target)

    local_mmdc = _local_mmdc()
    if local_mmdc is not None:
        cmd = [
            str(local_mmdc),
            "--input",
            str(tmp_in_path),
            "--output",
            str(tmp_out_path),
            "--backgroundColor",
            background,
            "--scale",
            str(scale),
            "--theme",
            theme,
            "--quiet",
        ]
    else:
        cmd = [
            _npx_command(),
            "--yes",
            MERMAID_CLI_PACKAGE,
            "--input",
            str(tmp_in_path),
            "--output",
            str(tmp_out_path),
            "--backgroundColor",
            background,
            "--scale",
            str(scale),
            "--theme",
            theme,
            "--quiet",
        ]
    if config is not None:
        cmd.extend(["--configFile", str(config)])

    try:
        env = os.environ.copy()
        chromium = _find_chromium_exe()
        if chromium is not None:
            env["PUPPETEER_EXECUTABLE_PATH"] = str(chromium)
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        if not tmp_out_path.exists():
            msg = f"rendered file missing: {tmp_out_path}"
            raise FileNotFoundError(msg)
        tmp_out_path.replace(target)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr or exc.stdout or str(exc)
        return False, f"mermaid-cli exit {exc.returncode}: {detail}".strip()
    except OSError as exc:
        return False, str(exc)
    finally:
        tmp_in_path.unlink(missing_ok=True)
        if tmp_out_path.exists():
            tmp_out_path.unlink()

    return True, result.stderr or result.stdout or ""


def _render_all(
    paths: Iterable[Path],
    background: str,
    scale: float,
    theme: str,
    config: Path | None,
) -> None:
    errors: list[tuple[Path, str]] = []
    for diagram_path in paths:
        ok, message = _render_diagram(
            diagram_path,
            background=background,
            scale=scale,
            theme=theme,
            config=config,
        )
        if ok:
            continue
        errors.append((diagram_path, message))
        logger.error("Failed to render %s: %s", diagram_path, message)

    if errors:
        raise RuntimeError(f"{len(errors)} diagram(s) failed")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    args = _parse_args()
    _cleanup_temp(args.root)
    diagrams = _find_diagrams(args.root)
    if not diagrams:
        logger.warning("No diagrams (*.mmd) found in %s", args.root)
        return 1

    try:
        _render_all(
            diagrams,
            background=args.background,
            scale=args.scale,
            theme=args.theme,
            config=args.config,
        )
    except RuntimeError as exc:
        logger.error("Rendering failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
