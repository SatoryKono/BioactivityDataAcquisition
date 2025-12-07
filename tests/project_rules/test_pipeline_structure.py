from __future__ import annotations

from pathlib import Path

import pytest

STAGE_FILES = {"extract.py", "transform.py", "validate.py", "export.py"}


def _expected_pipeline_dirs(configs_root: Path) -> set[tuple[str, str]]:
    base = configs_root / "pipelines"
    pairs: set[tuple[str, str]] = set()
    for provider_dir in base.glob("*"):
        if not provider_dir.is_dir():
            continue
        provider = provider_dir.name
        for config_file in provider_dir.glob("*.yaml"):
            pairs.add((provider, config_file.stem))
    return pairs


def test_pipeline_directories_and_docs(
    bioetl_root: Path,
    configs_root: Path,
    docs_root: Path,
) -> None:
    expected = _expected_pipeline_dirs(configs_root)
    violations: list[str] = []

    for provider, entity in sorted(expected):
        pipeline_dir = bioetl_root / "application" / "pipelines" / provider / entity
        if not pipeline_dir.exists():
            violations.append(
                f"Отсутствует каталог пайплайна {pipeline_dir.as_posix()}"
            )
            continue

        present = {p.name for p in pipeline_dir.iterdir() if p.is_file()}
        for stage_file in STAGE_FILES:
            if stage_file not in present:
                violations.append(
                    f"{pipeline_dir.as_posix()}: отсутствует файл этапа {stage_file}"
                )

        docs_dir = docs_root / "application" / "pipelines" / provider / entity
        has_docs = docs_dir.exists() and any(
            p.suffix == ".md" for p in docs_dir.rglob("*.md")
        )
        if not has_docs:
            violations.append(
                f"Нет документации для {provider}/{entity} в {docs_dir.as_posix()}"
            )

    if violations:
        pytest.fail("\n".join(violations))
