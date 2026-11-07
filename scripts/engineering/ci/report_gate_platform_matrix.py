"""Generate the static GitHub Actions and CircleCI gate matrix."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

CIRCLE = Path(".circleci/config.yml")
OUTPUT = Path("docs/ci/gate-platform-matrix-full.md")
GITHUB = Path(".github/workflows")
PAIRS = {
    "classify": ("pr-required.yml:classify-changes",),
    "lint-ruff": ("pr-required.yml:class-lane",),
    "lint-arch": ("pr-required.yml:class-lane",),
    "arch-tests": ("pr-required.yml:class-lane",),
    "mypy": ("pr-required.yml:class-lane",),
    "dependency-lock": ("tests.yml:dependency-preflight",),
    "test-fast": ("tests.yml:test-fast",),
    "test-integration": ("tests.yml:test-matrix",),
    "dq-consistency": ("tests.yml:dq-consistency-gate",),
    "root-hygiene": (
        "root-hygiene.yml:root-hygiene",
        "pr-required.yml:fast-governance",
    ),
    "compiled-artifacts": (
        "compiled-artifacts-block.yml:check-artifacts",
        "pr-required.yml:fast-governance",
    ),
    "security-scans": ("security.yml:security-scans",),
    "actions-audit": (
        "zizmor.yml:zizmor",
        "pr-required.yml:fast-governance",
    ),
    "docs-diagrams": ("diagram-nightly.yml:docs-diagrams",),
    "duplication": ("duplication-complexity.yml:duplication",),
    "schema-governance": ("schema-governance.yml:schema-governance",),
    "semantic-governance": ("semantic-governance.yml:semantic-governance",),
    "commit-lint": (
        "commit-lint.yml:commit-lint",
        "pr-required.yml:fast-governance",
    ),
    "docs-governance": ("docs.yml:docs-governance",),
    "docker-build": (
        "pr-required.yml:docker-lane",
        "docker.yml:docker-lint",
        "docker.yml:docker-compose-validate",
        "docker.yml:docker-build",
    ),
    "port-contracts": ("port-contracts.yml:port-contracts",),
    "provider-contract-drift": ("provider-contract-drift.yml:replay-gate",),
    "memory-freshness": ("memory-freshness.yml:memory-freshness",),
    "skills-consistency": ("skills-consistency.yml:skills-consistency",),
    "e2e-matrix-replay": ("e2e-matrix-health.yml:matrix-smoke-blocking",),
    "pr-gate-complete": ("pr-required.yml:pr-gate-complete",),
}
DOCKER_COMPONENTS = (
    "docker.yml:docker-lint",
    "docker.yml:docker-compose-validate",
    "docker.yml:docker-build",
)
COVERAGE = re.compile(
    r"(?<!\S)(?:--cov(?:=\S+)?|(?:python\s+-m\s+)?coverage\s+run)(?=\s|$)"
)


def job_lines(path: Path) -> dict[str, int]:
    root = yaml.compose(path.read_text(encoding="utf-8"))
    jobs = next(value for key, value in root.value if key.value == "jobs")
    return {key.value: key.start_mark.line + 1 for key, _ in jobs.value}


def commands(job: dict) -> str:
    runs = (
        step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)
    )
    chunks = (run.get("command", "") if isinstance(run, dict) else run for run in runs)
    return "\n".join(
        re.sub(r"\s+#.*$", "", line)
        for chunk in chunks
        for line in chunk.splitlines()
        if not line.lstrip().startswith("#")
    )


def features(job: dict, matrix: object) -> str:
    parts = []
    for key in ("runs-on", "executor", "resource_class"):
        if job.get(key):
            parts.append(f"{key}={job[key]}")
    if matrix:
        parts.append("matrix")
    shell = commands(job)
    for name in ("uv", "pytest", "ruff", "mypy", "hypothesis"):
        if re.search(rf"\b{name}\b", shell, re.IGNORECASE):
            parts.append(name)
    if any(
        COVERAGE.search(line) and "--no-cov" not in line for line in shell.splitlines()
    ):
        parts.append("cov:yes")
    return ", ".join(parts) or "—"


def cell(value: object) -> str:
    if value is None:
        return "—"
    return json.dumps(value, ensure_ascii=False).replace("|", "&#124;")


def row(*values: str) -> str:
    return "| " + " | ".join(value.replace("|", "&#124;") for value in values) + " |"


def render() -> str:
    circle = yaml.safe_load(CIRCLE.read_text(encoding="utf-8"))
    lane = circle["workflows"]["pr-gate"]
    entries = [
        next(iter(item.items())) if isinstance(item, dict) else (item, {})
        for item in lane["jobs"]
    ]
    aggregate = set(dict(entries)["pr-gate-complete"]["requires"])
    circle_lines = job_lines(CIRCLE)

    github = {}
    for path in sorted(GITHUB.iterdir()):
        if path.suffix not in {".yml", ".yaml"}:
            continue
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, line in job_lines(path).items():
            github[f"{path.name}:{name}"] = (
                workflow["jobs"][name],
                path,
                line,
                workflow.get("on", workflow.get(True)),
            )

    lines = [
        "# Статическая матрица гейтов GitHub Actions и CircleCI",
        "",
        "Проверка воспроизводимости: `python -m scripts.engineering.ci gate-platform-matrix --check`.",
        "",
        "Сравнение охватывает все вызовы в CircleCI `pr-gate` и все определения jobs",
        "в `.github/workflows/`. Статическое сопоставление не подтверждает",
        "эквивалентность запусков. Для `[EQ?]` нужны парные прогоны и сравнение условий отказа.",
        "",
        "Условие CircleCI для всего lane: " + cell(lane.get("when")) + ".",
        "Колонка агрегатора CircleCI показывает прямую зависимость `pr-gate-complete`;",
        "фильтры запуска вынесены отдельно. Запуск GitHub ограничивают события",
        "workflow и условие job. `[UNIQUE-GH]` означает отсутствие пары в CircleCI",
        "`pr-gate`, а `[UNIQUE-CCI]` — отсутствие установленной пары в GitHub.",
        "",
        "| CircleCI job | GitHub job | Статус | CircleCI признаки | GitHub признаки | CircleCI фильтры | В агрегаторе CircleCI | GitHub события и условие |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    mapped = set()
    for name, params in entries:
        label = params.get("name", name)
        call = f"`{label}` ({CIRCLE.as_posix()}:{circle_lines[name]})"
        cci_features = features(circle["jobs"][name], params.get("matrix"))
        member = (
            "агрегатор"
            if name == "pr-gate-complete"
            else ("да" if label in aggregate else "нет")
        )
        filters = cell(params.get("filters"))
        candidates = [
            candidate for candidate in PAIRS.get(name, ()) if candidate in github
        ]
        if not candidates:
            lines.append(
                row(
                    call,
                    "контур не найден",
                    "[UNIQUE-CCI]",
                    cci_features,
                    "—",
                    filters,
                    member,
                    "—",
                )
            )
        for candidate in candidates:
            job, path, line, events = github[candidate]
            mapped.add(candidate)
            relation = (
                "[DIFF]"
                if candidate in DOCKER_COMPONENTS
                or candidate == "pr-required.yml:fast-governance"
                else "[EQ?]"
            )
            lines.append(
                row(
                    call,
                    f"`{candidate}` ({path.as_posix()}:{line})",
                    relation,
                    cci_features,
                    features(job, job.get("strategy", {}).get("matrix")),
                    filters,
                    member,
                    f"{cell(events)} / {cell(job.get('if'))}",
                )
            )

    for candidate, (job, path, line, events) in github.items():
        if candidate not in mapped:
            lines.append(
                row(
                    "контур не найден",
                    f"`{candidate}` ({path.as_posix()}:{line})",
                    "[UNIQUE-GH]",
                    "—",
                    features(job, job.get("strategy", {}).get("matrix")),
                    "—",
                    "—",
                    f"{cell(events)} / {cell(job.get('if'))}",
                )
            )
    lines.extend(
        (
            "",
            "CircleCI `docker-build` включает Hadolint и проверку обеих Compose-конфигураций.",
            "Эти шаги сопоставлены с отдельными GitHub jobs как части составной проверки.",
        )
    )
    lines.extend(
        (
            "",
            "GitHub `fast-governance` включает root hygiene, compiled-artifacts, commitlint и zizmor.",
            "Сопоставления относятся к отдельным шагам. Проверки закрепления reusable workflows",
            "и Dependency Review остаются дополнительными шагами GitHub в этой паре контуров.",
        )
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.check:
        return int(OUTPUT.read_text(encoding="utf-8") != content)
    OUTPUT.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
