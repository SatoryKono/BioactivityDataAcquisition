"""Generate a static inventory of GitHub Actions workflow jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

OUTPUT = Path("docs/ci/gate-platform-matrix-full.md")
GITHUB = Path(".github/workflows")


def cell(value: object) -> str:
    """Keep JSON-encoded workflow values inside one Markdown table cell."""
    if value is None:
        return "—"
    return json.dumps(value, ensure_ascii=False).replace("|", "&#124;")


def render() -> str:
    """List current workflow triggers, job conditions, dependencies and runners."""
    lines = [
        "# Статическая матрица заданий GitHub Actions",
        "",
        "Проверка воспроизводимости: `python -m scripts.engineering.ci gate-platform-matrix --check`.",
        "",
        "Матрица описывает определения jobs в `.github/workflows/` на текущем дереве.",
        "Триггеры workflow, условия и зависимости ограничивают фактический запуск;",
        "наличие job не доказывает её выполнение или обязательность для слияния PR.",
        "",
        "| Workflow: job | События workflow | Условие job | Зависимости | Runner или reusable workflow |",
        "| --- | --- | --- | --- | --- |",
    ]
    for path in sorted(GITHUB.iterdir()):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        source = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(source)
        root = yaml.compose(source)
        jobs_node = next(value for key, value in root.value if key.value == "jobs")
        events = workflow.get("on", workflow.get(True))
        for name_node, job_node in jobs_node.value:
            name = name_node.value
            job = workflow["jobs"][name]
            line = name_node.start_mark.line + 1
            identifier = f"`{path.name}:{name}` ({path.as_posix()}:{line})"
            runner = job.get("runs-on", job.get("uses"))
            if (
                path.name == "codeql.yml"
                and name == "analyze"
                and isinstance(runner, str)
            ):
                runner_end = next(
                    (
                        value.end_mark
                        for key, value in job_node.value
                        if key.value == "runs-on"
                        and key.start_mark.line == value.end_mark.line
                    ),
                    None,
                )
                if runner_end is not None:
                    tail = source.splitlines()[runner_end.line][runner_end.column :]
                    note = tail.partition("#")[2].strip()
                    if note.startswith("canary-verified: "):
                        runner = f"{runner}, {note}"
            values = (
                identifier,
                cell(events),
                cell(job.get("if")),
                cell(job.get("needs")),
                cell(runner),
            )
            lines.append(
                "| "
                + " | ".join(value.replace("|", "&#124;") for value in values)
                + " |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.check:
        return int(
            not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content
        )
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
