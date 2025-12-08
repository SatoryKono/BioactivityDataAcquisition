from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

MERMAID_CLI_VERSION = "10.9.1"
MERMAID_CLI_PACKAGE = f"@mermaid-js/mermaid-cli@{MERMAID_CLI_VERSION}"

_FRONT_MATTER_PATTERN = re.compile(
    r"^---\s*[\r\n].*?[\r\n]---\s*[\r\n]?", flags=re.DOTALL
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render all Mermaid (*.mmd) diagrams under the given root to PNG."
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
    return parser.parse_args()


def _npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def _strip_front_matter(content: str) -> str:
    match = _FRONT_MATTER_PATTERN.match(content)
    if match is None:
        return content
    return content[match.end() :]


def _sanitize_mermaid(content: str) -> str:
    """Remove style fragments that trigger mermaid-cli parser bugs.

    Some combinations of ``color:#...`` and ``font-size:...`` in ``classDef`` and
    ``linkStyle`` definitions cause parse errors on Windows when rendered via
    mermaid-cli 10.9.x. We strip these attributes, сохраняя остальную разметку
    диаграммы.
    """

    def _sanitize_line(line: str) -> str:
        # remove `, color:#xxxxxx`-like fragments
        line = re.sub(r",\s*color:#(?:[0-9a-fA-F]{3,6})", "", line)
        # remove `, font-size:22px`-like fragments
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


def _render_diagram(path: Path, background: str, scale: float) -> tuple[bool, str]:
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

    print(f"[render] {path} -> {target} (tmp_in={tmp_in_path}, tmp_out={tmp_out_path})")

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
        "--quiet",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if not tmp_out_path.exists():
            raise FileNotFoundError(f"rendered file missing: {tmp_out_path}")
        tmp_out_path.replace(target)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr or exc.stdout or str(exc)
        return False, f"mermaid-cli exit {exc.returncode}: {detail}".strip()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        tmp_in_path.unlink(missing_ok=True)
        if tmp_out_path.exists():
            tmp_out_path.unlink()

    return True, result.stderr or result.stdout or ""


def _render_all(paths: Iterable[Path], background: str, scale: float) -> None:
    errors: list[tuple[Path, str]] = []
    for diagram_path in paths:
        ok, message = _render_diagram(diagram_path, background=background, scale=scale)
        if ok:
            continue
        errors.append((diagram_path, message))
        print(f"[error] {diagram_path}: {message}", file=sys.stderr)

    if errors:
        raise RuntimeError(f"{len(errors)} diagram(s) failed")


def main() -> int:
    args = _parse_args()
    _cleanup_temp(args.root)
    diagrams = _find_diagrams(args.root)
    if not diagrams:
        print(f"Диаграммы (*.mmd) не найдены в {args.root}", file=sys.stderr)
        return 1

    try:
        _render_all(diagrams, background=args.background, scale=args.scale)
    except subprocess.CalledProcessError as exc:
        print(
            f"mermaid-cli завершилась с ошибкой {exc.returncode} для {exc.cmd}",
            file=sys.stderr,
        )
        return exc.returncode
    except Exception as exc:  # noqa: BLE001
        print(f"Ошибка рендеринга: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
