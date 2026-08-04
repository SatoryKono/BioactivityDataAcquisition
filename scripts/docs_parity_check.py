#!/usr/bin/env python3
"""
Documentation Parity Check Script

Validates that documentation stays in sync with code and configuration.
Implements the parity gate requirements from the governance framework.
"""

import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

try:
    import tomllib as toml
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import toml  # type: ignore[no-redef]  # pyright: ignore[reportMissingModuleSource, reportMissingImports]


@dataclass
class ParityResult:
    """Result of a parity check."""

    total_checked: int
    matches: int
    mismatches: int
    missing_docs: list[str]
    missing_code: list[str]
    parity_percentage: float

    def is_critical(self) -> bool:
        """Check if parity issues are critical (block merge)."""
        return self.parity_percentage < 85.0 or len(self.missing_docs) > 5

    def is_error(self) -> bool:
        """Check if parity issues are errors (require attention)."""
        return self.parity_percentage < 90.0

    def is_warning(self) -> bool:
        """Check if parity issues are warnings (should be addressed)."""
        return self.parity_percentage < 95.0


@dataclass
class ConfigEntity:
    """Represents a configuration entity that should have documentation."""

    name: str
    type: str
    path: str
    has_docs: bool = False
    doc_path: str | None = None


class DocumentationParityChecker:
    """Main class for checking documentation parity."""

    def __init__(self):
        self.configs_dir = Path("configs")
        self.docs_dir = Path("docs")
        self.pipeline_specs_dir = self.docs_dir / "04-reference" / "pipelines"
        self.entity_configs_dir = self.configs_dir / "entities"
        self.composite_configs_dir = self.configs_dir / "composites"

    def _provider_entity_config_files(self, provider_dir: Path) -> list[Path]:
        """Return visible entity config files for one provider directory."""
        return list(
            filter(
                self._is_visible_config_file, self._provider_yaml_files(provider_dir)
            )
        )

    def _provider_yaml_files(self, provider_dir: Path) -> list[Path]:
        """Return provider YAML files before visibility filtering."""
        return sorted(provider_dir.glob("*.yaml"))

    def _is_visible_config_file(self, config_file: Path) -> bool:
        """Return whether a provider config file participates in parity checks."""
        return not config_file.name.startswith("_")

    def _iter_entity_config_files(self) -> list[Path]:
        if not self.entity_configs_dir.exists():
            return []
        return [
            config_file
            for provider_dir in sorted(self.entity_configs_dir.iterdir())
            if provider_dir.is_dir()
            for config_file in self._provider_entity_config_files(provider_dir)
        ]

    def _iter_composite_config_files(self) -> list[Path]:
        if not self.composite_configs_dir.exists():
            return []
        return list(self.composite_configs_dir.glob("*.yaml"))

    def _iter_pipeline_doc_files(self) -> list[Path]:
        """Return pipeline-spec docs when the docs tree exists."""
        if not self.pipeline_specs_dir.exists():
            return []
        return list(self.pipeline_specs_dir.glob("*/*spec.md"))

    def _iter_entity_doc_files(self) -> list[Path]:
        """Return entity reference docs when the docs tree exists."""
        entity_docs_dir = self.docs_dir / "04-reference" / "entity-specs"
        if not entity_docs_dir.exists():
            return []
        return list(entity_docs_dir.glob("*.md"))

    def _config_entity(self, config_file: Path, *, entity_type: str) -> ConfigEntity:
        """Build a ConfigEntity from one config file."""
        return ConfigEntity(
            name=config_file.stem,
            type=entity_type,
            path=str(config_file.relative_to(self.configs_dir)),
        )

    def find_config_files(self) -> list[ConfigEntity]:
        """Find all configuration files that should have documentation."""
        config_entities = [
            self._config_entity(config_file, entity_type="entity")
            for config_file in self._iter_entity_config_files()
        ]
        config_entities.extend(
            self._config_entity(config_file, entity_type="composite")
            for config_file in self._iter_composite_config_files()
        )
        return config_entities

    def find_documentation_files(self) -> list[Path]:
        """Find all pipeline specification documentation files."""
        doc_files = self._iter_pipeline_doc_files()
        doc_files.extend(self._iter_entity_doc_files())
        return doc_files

    def extract_config_metadata(self, config_path: Path) -> dict[str, str]:
        """Extract metadata from a configuration file."""

        try:
            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                return yaml.safe_load(config_path.read_bytes()) or {}
            elif config_path.suffix == ".toml":
                return toml.loads(config_path.read_text(encoding="utf-8"))
            elif config_path.suffix == ".json":
                return json.loads(config_path.read_text(encoding="utf-8"))
            else:
                return {}
        except Exception as e:
            print(f"⚠️  Error reading config {config_path}: {e}")
            return {}

    def extract_doc_metadata(self, doc_path: Path) -> dict[str, str]:
        """Extract metadata from a documentation file."""

        metadata = {
            "title": "",
            "description": "",
            "entity": "",
            "type": "",
            "status": "active",
        }

        try:
            content = doc_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            metadata.update(self._parse_front_matter_metadata(content, doc_path))

            # Extract title from first header if no front matter
            if not metadata.get("title"):
                for line in lines:
                    if line.startswith("# "):
                        metadata["title"] = line[2:].strip()
                        break

            # Try to extract entity name from title or content
            if not metadata.get("entity"):
                metadata["entity"] = self._infer_entity_name(
                    metadata.get("title", ""),
                    doc_path,
                )

            return metadata

        except Exception as e:
            print(f"⚠️  Error reading doc {doc_path}: {e}")
            return metadata

    def _parse_front_matter_metadata(
        self, content: str, doc_path: Path
    ) -> dict[str, str]:
        if not content.startswith("---"):
            return {}
        front_matter_end = content.find("\n---", 1)
        if front_matter_end == -1:
            return {}
        front_matter = content[3:front_matter_end].strip()
        try:
            return yaml.safe_load(front_matter) or {}
        except Exception as e:
            print(f"⚠️  Error parsing front matter in {doc_path}: {e}")
            return {}

    def _infer_entity_name(self, title: str, doc_path: Path) -> str:
        path_stem = doc_path.stem.replace("-spec", "")
        path_parts = path_stem.split("-")
        if path_parts and path_parts[0].isdigit():
            path_parts = path_parts[1:]
        if path_parts:
            return "_".join(path_parts)
        title_lower = title.lower()
        if "entity" in title_lower or "pipeline" in title_lower:
            parts = title_lower.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
        return path_stem.replace("pipeline-", "")

    def match_configs_to_docs(self, configs: list[ConfigEntity]) -> list[ConfigEntity]:
        """Match configuration entities to their documentation."""

        doc_files = self.find_documentation_files()
        doc_metadata_cache = {}

        # Build documentation metadata cache
        for doc_file in doc_files:
            metadata = self.extract_doc_metadata(doc_file)
            entity_name = metadata.get("entity", "").lower()
            if entity_name:
                doc_metadata_cache[entity_name] = (doc_file, metadata)

        # Match configs to docs
        for config in configs:
            config_name = config.name.lower()

            # Try exact match first
            if config_name in doc_metadata_cache:
                doc_file, metadata = doc_metadata_cache[config_name]
                config.has_docs = True
                config.doc_path = str(doc_file)
                continue

            # Try partial matches (e.g., "chembl_molecule" vs "molecule")
            for doc_entity, (doc_file, metadata) in doc_metadata_cache.items():
                if config_name.endswith(doc_entity) or doc_entity.endswith(config_name):
                    config.has_docs = True
                    config.doc_path = str(doc_file)
                    break

        return configs

    def check_parity(self) -> ParityResult:
        """Check documentation parity for all configuration entities."""

        # Find all configs that should have documentation
        configs = self.find_config_files()

        if not configs:
            return ParityResult(
                total_checked=0,
                matches=0,
                mismatches=0,
                missing_docs=[],
                missing_code=[],
                parity_percentage=100.0,
            )

        # Match configs to existing docs
        matched_configs = self.match_configs_to_docs(configs)

        # Calculate parity metrics
        matches = sum(1 for config in matched_configs if config.has_docs)
        mismatches = len(matched_configs) - matches

        missing_docs = [
            f"{config.type}:{config.name} ({config.path})"
            for config in matched_configs
            if not config.has_docs
        ]

        # Check for docs without corresponding configs
        doc_files = self.find_documentation_files()
        doc_entities = set()

        for doc_file in doc_files:
            metadata = self.extract_doc_metadata(doc_file)
            entity = metadata.get("entity", "")
            if entity:
                doc_entities.add(entity.lower())

        config_entities = {config.name.lower() for config in matched_configs}
        missing_code = [f"doc:{entity}" for entity in doc_entities - config_entities]

        parity_percentage = (
            (matches / len(matched_configs) * 100) if matched_configs else 100.0
        )

        return ParityResult(
            total_checked=len(matched_configs),
            matches=matches,
            mismatches=mismatches,
            missing_docs=missing_docs,
            missing_code=list(missing_code),
            parity_percentage=parity_percentage,
        )

    def generate_report(self, result: ParityResult) -> str:
        """Generate a detailed parity report."""

        report = []
        report.append("# 📊 Documentation Parity Report")
        report.append("")
        report.append(
            f"**Generated**: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}"
        )
        report.append(f"**Total Configs Checked**: {result.total_checked}")
        report.append(
            "**Documentation Coverage**: "
            f"{result.matches}/{result.total_checked} "
            f"({result.parity_percentage:.1f}%)"
        )
        report.append("")

        # Status badge
        if result.is_critical():
            report.append("🔴 **Status: CRITICAL - Merge blocked**")
        elif result.is_error():
            report.append("🟡 **Status: ERROR - Requires attention**")
        elif result.is_warning():
            report.append("🟠 **Status: WARNING - Should be addressed**")
        else:
            report.append("🟢 **Status: PASS - Parity requirements met**")

        report.append("")

        # Missing documentation section
        if result.missing_docs:
            report.append("## ❌ Missing Documentation")
            report.append("")
            report.append("Configurations without corresponding documentation:")
            report.append("")
            for item in sorted(result.missing_docs):
                report.append(f"- `{item}`")
            report.append("")

        # Orphaned documentation section
        if result.missing_code:
            report.append("## ⚠️  Orphaned Documentation")
            report.append("")
            report.append("Documentation without corresponding configuration:")
            report.append("")
            for item in sorted(result.missing_code):
                report.append(f"- `{item}`")
            report.append("")

        # Summary and recommendations
        report.append("## 🎯 Recommendations")
        report.append("")

        if result.is_critical():
            report.append(
                "- 🔴 **CRITICAL**: Merge blocked due to missing documentation"
            )
            report.append(
                "- Create documentation for all missing configurations before merging"
            )
            report.append(
                "- Consider removing orphaned documentation or linking to active configs"
            )
        elif result.is_error():
            report.append(
                "- 🟡 **ERROR**: Documentation parity below acceptable threshold"
            )
            report.append(
                "- Prioritize creating documentation for missing configurations"
            )
            report.append("- Review orphaned documentation for cleanup")
        elif result.is_warning():
            report.append("- 🟠 **WARNING**: Documentation parity could be improved")
            report.append("- Address missing documentation in next iteration")
            report.append("- Consider automating documentation generation")
        else:
            report.append("- 🟢 **PASS**: Documentation parity requirements met")
            report.append("- Continue maintaining documentation with code changes")
            report.append("- Monitor for any parity drift")

        report.append("")
        report.append("## 📋 Thresholds")
        report.append("")
        report.append("- **Block**: <85% parity or >5 missing critical docs")
        report.append("- **Error**: <90% parity")
        report.append("- **Warning**: <95% parity")
        report.append("- **Pass**: ≥95% parity")

        return "\n".join(report)

    def generate_json_report(self, result: ParityResult) -> dict[str, object]:
        """Generate a JSON report for CI/CD integration."""

        return {
            "timestamp": subprocess.run(
                ["date", "--iso-8601=seconds"], capture_output=True, text=True
            ).stdout.strip(),
            "metrics": {
                "total_checked": result.total_checked,
                "matches": result.matches,
                "mismatches": result.mismatches,
                "parity_percentage": result.parity_percentage,
                "missing_docs_count": len(result.missing_docs),
                "missing_code_count": len(result.missing_code),
            },
            "status": self._status_label(result),
            "missing_docs": result.missing_docs,
            "missing_code": result.missing_code,
            "thresholds": {"block": 85.0, "error": 90.0, "warning": 95.0, "pass": 95.0},
        }

    @staticmethod
    def _status_label(result: ParityResult) -> str:
        if result.is_critical():
            return "critical"
        if result.is_error():
            return "error"
        if result.is_warning():
            return "warning"
        return "pass"


def main():
    """Main entry point."""

    checker = DocumentationParityChecker()
    result = checker.check_parity()

    # Generate and display report
    report = checker.generate_report(result)
    print(report)

    # Generate JSON report for CI/CD
    json_report = checker.generate_json_report(result)

    # Write JSON report for CI/CD consumption
    report_file = Path("docs/reports/docs-parity-report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2)

    print(f"\n📊 JSON report written to: {report_file}")

    # Exit with appropriate code
    if result.is_critical():
        print(
            "\n❌ CRITICAL: Documentation parity requirements not met - merge blocked"
        )
        sys.exit(1)
    elif result.is_error():
        print("\n⚠️  ERROR: Documentation parity below threshold - requires attention")
        sys.exit(1)
    elif result.is_warning():
        print("\n⚠️  WARNING: Documentation parity could be improved")
        sys.exit(0)  # Don't block, but warn
    else:
        print("\n✅ PASS: Documentation parity requirements met")
        sys.exit(0)


if __name__ == "__main__":
    main()
