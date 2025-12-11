from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping

import yaml


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return current


def _read_yaml_mapping(path: Path) -> Mapping[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _parse_index_entries(text: str) -> set[str]:
    pattern = re.compile(r"^- `([^`]+)`", flags=re.MULTILINE)
    return set(pattern.findall(text))


def _iter_pipeline_config_names(config_root: Path) -> set[str]:
    names: set[str] = set()
    for path in config_root.rglob("*.yaml"):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        pipeline = payload.get("pipeline") or {}
        name = pipeline.get("name")
        if name:
            names.add(str(name))
    return names


@dataclass
class SectionResult:
    title: str
    missing: list[str]
    unused: list[str]

    @property
    def has_issues(self) -> bool:
        return bool(self.missing or self.unused)

    def render(self) -> str:
        missing = ", ".join(self.missing) if self.missing else "none"
        unused = ", ".join(self.unused) if self.unused else "none"
        return f"- {self.title}: missing=[{missing}], unused=[{unused}]"


@dataclass
class RegistrySyncReport:
    sections: list[SectionResult]

    @property
    def has_issues(self) -> bool:
        return any(section.has_issues for section in self.sections)

    def render(self) -> str:
        lines = ["Registry sync report:"]
        lines.extend(section.render() for section in self.sections)
        return "\n".join(lines)


def _compare_sets(title: str, expected: Iterable[str], actual: Iterable[str]) -> SectionResult:
    expected_set = set(expected)
    actual_set = set(actual)
    missing = sorted(expected_set - actual_set)
    unused = sorted(actual_set - expected_set)
    return SectionResult(title=title, missing=missing, unused=unused)


def build_sync_report() -> RegistrySyncReport:
    root = _find_project_root(Path(__file__))
    sys.path.insert(0, str(root / "src"))

    registry_path = root / "src/bioetl/infrastructure/clients/base/abc_registry.yaml"
    impl_paths = [
        root / "src/bioetl/infrastructure/clients/base/abc_impls.yaml",
        root / "src/bioetl/interfaces/abc_impls_application.yaml",
    ]
    index_paths = [root / "docs/ABC_INDEX.md", root / "docs/01-ABC/INDEX.md"]
    config_root = root / "configs/pipelines"

    from bioetl.application.pipelines.registry import PIPELINE_REGISTRY

    registry_names = _read_yaml_mapping(registry_path).keys()

    impl_names: set[str] = set()
    for path in impl_paths:
        impl_names.update(_read_yaml_mapping(path).keys())
    pipeline_registry_names = PIPELINE_REGISTRY.keys()
    pipeline_config_names = _iter_pipeline_config_names(config_root)

    sections: list[SectionResult] = [
        _compare_sets(
            "abc_impls.yaml vs abc_registry.yaml",
            expected=registry_names,
            actual=impl_names,
        ),
    ]

    for path in index_paths:
        index_names = _parse_index_entries(path.read_text(encoding="utf-8"))
        sections.append(
            _compare_sets(
                f"{path.relative_to(root)} vs abc_registry.yaml",
                expected=registry_names,
                actual=index_names,
            )
        )

    sections.append(
        _compare_sets(
            "pipeline configs vs application registry",
            expected=pipeline_registry_names,
            actual=pipeline_config_names,
        )
    )

    return RegistrySyncReport(sections=sections)


def main() -> int:
    report = build_sync_report()
    print(report.render())
    return 1 if report.has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
