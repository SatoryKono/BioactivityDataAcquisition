from __future__ import annotations

import re
import textwrap
from pathlib import Path

BASE = Path("docs/architecture/diagrams")
TARGETS = [
    Path("docs/architecture/06-architecture-diagrams.md"),
    Path("docs/architecture/07-diagrams.md"),
    Path("docs/architecture/11-component-diagram.md"),
    Path("docs/architecture/12-class-diagrams-interfaces.md"),
    Path("docs/architecture/13-class-diagrams-application.md"),
    Path("docs/architecture/14-class-diagrams-domain.md"),
    Path("docs/architecture/15-class-diagrams-infrastructure.md"),
    Path("docs/architecture/diagrams.md"),
]

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
CODE_START = re.compile(r"^```mermaid\s*$")
SLUG_CACHE: set[str] = set()


def slugify(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw.strip().lower()).strip("-") or "diagram"
    base_slug = slug
    i = 1
    while slug in SLUG_CACHE:
        i += 1
        slug = f"{base_slug}-{i}"
    SLUG_CACHE.add(slug)
    return slug


def ensure_dirs() -> None:
    for sub in ("class", "sequence", "flow"):
        (BASE / sub).mkdir(parents=True, exist_ok=True)


def extract(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8").splitlines()
    current_heading = path.stem
    in_code = False
    buffer: list[str] = []
    diagrams: list[tuple[str, str]] = []

    for line in text:
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level, title = heading_match.groups()
            if level == "##":
                current_heading = title

        if in_code:
            if line.strip() == "```":
                diagrams.append((current_heading, "\n".join(buffer)))
                buffer = []
                in_code = False
            else:
                buffer.append(line)
        else:
            if CODE_START.match(line):
                in_code = True
                buffer = []
    return diagrams


def detect_type(body: str) -> str:
    lower = body.lower()
    if "classdiagram" in lower:
        return "class"
    if "sequencediagram" in lower:
        return "sequence"
    if "flowchart" in lower:
        return "flow"
    return "flow"


def main() -> None:
    ensure_dirs()
    for path in TARGETS:
        diagrams = extract(path)
        for idx, (heading, body) in enumerate(diagrams, start=1):
            dtype = detect_type(body)
            slug = slugify(f"{path.stem}-{idx}-{heading}")
            out = BASE / dtype / f"{slug}.mmd"
            out.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
            print(out)


if __name__ == "__main__":
    main()

