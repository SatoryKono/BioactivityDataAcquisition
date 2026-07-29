#!/usr/bin/env python3
"""
ADR Registry Generator

Generates a comprehensive registry of Architecture Decision Records (ADRs)
with metadata for the project navigator. Implements issue #3090.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import yaml


class ADRJsonRegistryEntry(TypedDict):
    adr_number: str
    title: str
    file_path: str
    status: str
    source_status: str | None
    category: str
    owner: str
    decision_date: str | None
    last_reviewed: str | None
    context: str
    decision: str
    consequences: str
    supersedes: list[str]
    superseded_by: list[str]
    related: list[str]
    tags: list[str]


class ADRJsonRegistryStats(TypedDict):
    by_status: dict[str, int]
    by_category: dict[str, int]


class ADRJsonRegistry(TypedDict):
    generated: str
    total_adrs: int
    adrs: list[ADRJsonRegistryEntry]
    stats: ADRJsonRegistryStats


@dataclass
class ADRMetadata:
    """Metadata for an Architecture Decision Record."""

    # Basic information
    adr_number: str
    title: str
    file_path: str

    # Status information
    status: str = "accepted"
    source_status: str | None = None
    decision_date: str | None = None
    last_reviewed: str | None = None

    # Content information
    context: str = ""
    decision: str = ""
    consequences: str = ""

    # Relationships
    supersedes: list[str] = field(default_factory=list)
    superseded_by: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)

    # Categorization
    category: str = "architecture"
    tags: list[str] = field(default_factory=list)

    # Ownership
    owner: str = "BioETL Team"


class ADRRegistryGenerator:
    """Generates ADR registry with metadata."""

    def __init__(self) -> None:
        self.adr_dir = Path("docs/02-architecture/decisions")
        self.output_dir = Path("docs/02-architecture/adr-registry")
        self.navigator_registry_file = Path("docs/02-architecture/adr-registry.md")
        self.adr_index_file = self.adr_dir / "README.md"
        self.adr_index_metadata = self._load_adr_index_metadata()
        self.adrs: list[ADRMetadata] = []

    def _load_adr_index_metadata(self) -> dict[str, dict[str, str]]:
        """Load title/category/date/status metadata from the live ADR index table."""

        if not self.adr_index_file.exists():
            return {}

        pattern = re.compile(
            r"\|\s*\[ADR-(\d+)\]\([^)]+\)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|"
        )
        metadata_by_number: dict[str, dict[str, str]] = {}
        for line in self.adr_index_file.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line.strip())
            if match is None:
                continue
            adr_number, title, status, category, decision_date = (
                value.strip() for value in match.groups()
            )
            metadata_by_number[adr_number] = {
                "title": title,
                "status": status,
                "category": category,
                "decision_date": decision_date,
            }
        return metadata_by_number

    def find_adr_files(self) -> list[Path]:
        """Find all ADR files in the decisions directory."""

        if not self.adr_dir.exists():
            return []

        # Find all ADR files (ADR-XXX-*.md pattern)
        adr_files = []
        for file_path in self.adr_dir.glob("ADR-*.md"):
            adr_files.append(file_path)

        return sorted(adr_files)

    def extract_adr_number(self, file_path: Path) -> str | None:
        """Extract ADR number from filename."""

        match = re.match(r"ADR-(\d+)", file_path.stem)
        if match:
            return match.group(1)
        return None

    def parse_adr_front_matter(self, content: str) -> dict[str, object]:
        """Parse YAML front matter from ADR content."""

        metadata: dict[str, object] = {}

        if content.startswith("---"):
            front_matter_end = content.find("\n---", 1)
            if front_matter_end != -1:
                front_matter = content[3:front_matter_end].strip()
                try:
                    loaded = yaml.safe_load(front_matter)
                    if isinstance(loaded, dict):
                        metadata = loaded
                except Exception as e:
                    print(f"⚠️  Error parsing front matter: {e}")

        return metadata

    @staticmethod
    def _extract_inline_metadata_value(
        content: str,
        *,
        labels: tuple[str, ...],
    ) -> str | None:
        """Extract top-level metadata values from non-frontmatter ADR headers."""
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            normalized = stripped.replace("**", "").strip()
            for label in labels:
                pattern = re.compile(
                    rf"^{re.escape(label)}:\s*(.+)$", flags=re.IGNORECASE
                )
                match = pattern.match(normalized)
                if match is not None:
                    value = match.group(1).strip()
                    return value or None
        return None

    @classmethod
    def _normalized_registry_status(cls, raw_status: str | None) -> str:
        """Map explicit ADR statuses to registry buckets."""
        if not raw_status:
            return "accepted"
        base_status = raw_status.split("(", 1)[0].strip().lower()
        status_map = {
            "accepted": "accepted",
            "active": "accepted",
            "added": "draft",
            "draft": "draft",
            "deprecated": "deprecated",
            "superseded": "superseded",
            "archived": "archived",
        }
        return status_map.get(base_status, base_status or "accepted")

    @staticmethod
    def _normalize_metadata_value(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().strip("\"'").strip()
        if not normalized:
            return None
        if normalized.startswith("<") and normalized.endswith(">"):
            return None
        return normalized

    @staticmethod
    def _metadata_str_value(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _metadata_tags(value: object) -> list[str]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        return []

    def _date_from_table_line(self, line: str) -> str | None:
        if "|" not in line:
            return None
        lowered = line.lower()
        if "**дата**" not in lowered and "**date**" not in lowered:
            return None
        for cell in (cell.strip().strip("`") for cell in line.split("|")):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cell):
                return cell
        return None

    def _extract_decision_date(
        self,
        content: str,
        front_matter: dict[str, object],
        index_metadata: dict[str, str],
    ) -> str | None:
        candidates = (
            front_matter.get("date"),
            self._extract_inline_metadata_value(content, labels=("Date",)),
            index_metadata.get("decision_date"),
        )
        for candidate in candidates:
            normalized = self._normalize_metadata_value(
                candidate if isinstance(candidate, str) else None
            )
            if normalized is not None:
                return normalized
        for line in content.splitlines():
            found = self._date_from_table_line(line)
            if found is not None:
                return found
        return None

    @staticmethod
    def _parse_sortable_date(raw_date: str | None) -> tuple[int, str]:
        normalized = ADRRegistryGenerator._normalize_metadata_value(raw_date)
        if normalized is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            return (0, "0000-00-00")
        return (1, normalized)

    def extract_adr_sections(self, content: str) -> dict[str, str]:
        """Extract main sections from ADR content."""

        sections = {"context": "", "decision": "", "consequences": "", "status": ""}

        current_section = None
        lines = content.split("\n")

        for line in lines:
            # Skip front matter
            if line.startswith("---"):
                continue

            # Detect section headers
            if line.startswith("## "):
                section_title = line[3:].strip().lower()
                if section_title in sections:
                    current_section = section_title
                else:
                    current_section = None
            elif current_section and line.strip():
                # Add content to current section
                sections[current_section] += line + "\n"

        # Clean up sections
        for section in sections:
            sections[section] = sections[section].strip()
            # Limit length for metadata
            if len(sections[section]) > 200:
                sections[section] = sections[section][:197] + "..."

        return sections

    def extract_adr_relationships(self, content: str) -> dict[str, list[str]]:
        """Extract relationships (supersedes, related) from ADR content."""
        return {
            "supersedes": self._extract_relationship_ids(content, ("supersedes:",)),
            "superseded_by": self._extract_relationship_ids(
                content,
                ("superseded by:", "superseded_by:"),
            ),
            "related": self._extract_relationship_ids(content, ("related:",)),
        }

    @staticmethod
    def _extract_relationship_ids(
        content: str,
        markers: tuple[str, ...],
    ) -> list[str]:
        """Extract ADR identifiers from relationship-marked lines."""
        relationship_ids: set[str] = set()
        for line in content.splitlines():
            lowered = line.lower()
            if not any(marker in lowered for marker in markers):
                continue
            for adr_id in re.findall(r"ADR-\d+", line, flags=re.IGNORECASE):
                relationship_ids.add(adr_id.upper())
        return sorted(relationship_ids)

    def determine_adr_status(
        self,
        content: str,
        metadata: dict[str, object],
        *,
        relationships: dict[str, list[str]] | None = None,
    ) -> str:
        """Determine the status of an ADR."""

        # Check metadata first
        if metadata.get("status"):
            normalized = self._normalized_registry_status(str(metadata["status"]))
            if (
                normalized == "accepted"
                and relationships
                and relationships.get("superseded_by")
                and "partial" not in str(metadata["status"]).lower()
            ):
                return "superseded"
            return normalized

        inline_status = self._extract_inline_metadata_value(
            content,
            labels=("Status",),
        )
        if inline_status:
            normalized = self._normalized_registry_status(inline_status)
            if (
                normalized == "accepted"
                and relationships
                and relationships.get("superseded_by")
                and "partial" not in inline_status.lower()
            ):
                return "superseded"
            return normalized

        # Check for status indicators in content
        content_lower = content.lower()

        if "superseded by" in content_lower:
            return "superseded"
        elif "deprecated" in content_lower:
            return "deprecated"
        elif "archived" in content_lower:
            return "archived"
        elif "draft" in content_lower:
            return "draft"
        else:
            return "accepted"

    def extract_adr_metadata(self, file_path: Path) -> ADRMetadata | None:
        """Extract complete metadata from an ADR file."""

        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract basic information
            adr_number = self.extract_adr_number(file_path)
            if not adr_number:
                print(f"⚠️  Could not extract ADR number from {file_path}")
                return None
            index_metadata = self.adr_index_metadata.get(adr_number, {})

            # Parse front matter
            front_matter = self.parse_adr_front_matter(content)
            decision_date = self._extract_decision_date(
                content,
                front_matter,
                index_metadata,
            )
            last_reviewed = self._normalize_metadata_value(
                self._metadata_str_value(front_matter.get("last_reviewed"))
            ) or self._normalize_metadata_value(
                self._extract_inline_metadata_value(
                    content,
                    labels=("Last verified", "Last reviewed"),
                )
            )
            owner = self._normalize_metadata_value(
                self._metadata_str_value(front_matter.get("owner"))
            ) or self._normalize_metadata_value(
                self._extract_inline_metadata_value(
                    content,
                    labels=("Owner",),
                )
            )

            # Extract sections
            sections = self.extract_adr_sections(content)

            # Extract relationships
            relationships = self.extract_adr_relationships(content)

            # Determine status
            source_status = (
                self._normalize_metadata_value(
                    self._metadata_str_value(front_matter.get("status"))
                )
                or self._normalize_metadata_value(
                    self._extract_inline_metadata_value(content, labels=("Status",))
                )
                or self._normalize_metadata_value(index_metadata.get("status"))
            )
            status = self.determine_adr_status(
                content,
                {
                    **index_metadata,
                    **front_matter,
                },
                relationships=relationships,
            )

            resolved_title = self._metadata_str_value(
                front_matter.get("title")
            ) or index_metadata.get("title")
            resolved_category = self._metadata_str_value(
                front_matter.get("category")
            ) or index_metadata.get("category")

            # Create metadata object
            adr_metadata = ADRMetadata(
                adr_number=adr_number,
                title=resolved_title
                or file_path.stem.replace(f"ADR-{adr_number}-", "").replace("-", " "),
                file_path=str(file_path.relative_to(self.adr_dir)),
                status=status,
                source_status=source_status,
                decision_date=decision_date,
                last_reviewed=last_reviewed,
                context=sections.get("context", ""),
                decision=sections.get("decision", ""),
                consequences=sections.get("consequences", ""),
                supersedes=relationships.get("supersedes", []),
                superseded_by=relationships.get("superseded_by", []),
                related=relationships.get("related", []),
                category=resolved_category or "architecture",
                tags=self._metadata_tags(front_matter.get("tags", [])),
                owner=owner or "BioETL Team",
            )

            return adr_metadata

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return None

    def generate_adr_registry(self) -> list[ADRMetadata]:
        """Generate complete ADR registry."""

        adr_files = self.find_adr_files()

        if not adr_files:
            print("⚠️  No ADR files found")
            return []

        print(f"🔍 Found {len(adr_files)} ADR files")

        self.adrs = []

        for adr_file in adr_files:
            print(f"  Processing {adr_file.name}...")
            metadata = self.extract_adr_metadata(adr_file)
            if metadata:
                self.adrs.append(metadata)

        print(f"✅ Generated metadata for {len(self.adrs)} ADRs")

        return self.adrs

    def generate_registry_index(self, *, decision_link_prefix: str) -> str:
        """Generate the main ADR registry index page."""

        if not self.adrs:
            return "# ADR Registry\n\nNo ADRs found."

        status_groups = self._group_adrs_by_status()
        lines = []
        lines.append("# 📚 Architecture Decision Record (ADR) Registry")
        lines.append("")
        lines.append(
            "This registry provides a comprehensive index of all Architecture Decision Records"
        )
        lines.append("with metadata, status, and relationships.")
        lines.append("")
        lines.append(
            "Canonical live ADR index: `docs/02-architecture/decisions/README.md`."
        )
        lines.append(
            "This page is a generated governance mirror and MUST be regenerated via"
        )
        lines.append(
            "`python3 scripts/generate_adr_registry.py` after ADR additions or metadata changes."
        )
        lines.append("")
        lines.append(f"**Total ADRs**: {len(self.adrs)}")
        lines.append(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        self._append_status_summary(lines, status_groups)
        self._append_status_sections(
            lines,
            status_groups,
            decision_link_prefix=decision_link_prefix,
        )
        self._append_registry_footer(lines)
        return "\n".join(lines)

    def _group_adrs_by_status(self) -> dict[str, list[ADRMetadata]]:
        status_groups: dict[str, list[ADRMetadata]] = {}
        for adr in self.adrs:
            status_groups.setdefault(adr.status, []).append(adr)
        for status in status_groups:
            status_groups[status].sort(key=lambda x: x.adr_number)
        return status_groups

    def _append_status_summary(
        self,
        lines: list[str],
        status_groups: dict[str, list[ADRMetadata]],
    ) -> None:
        lines.append("## 📊 Status Summary")
        lines.append("")
        lines.append("| Status | Count | Percentage |")
        lines.append("|--------|-------|------------|")
        for status in sorted(status_groups.keys()):
            count = len(status_groups[status])
            percentage = count / len(self.adrs) * 100
            lines.append(f"| `{status}` | {count} | {percentage:.1f}% |")
        lines.append("")

    def _append_status_sections(
        self,
        lines: list[str],
        status_groups: dict[str, list[ADRMetadata]],
        *,
        decision_link_prefix: str,
    ) -> None:
        status_order = ["accepted", "draft", "deprecated", "superseded", "archived"]
        status_icons = {
            "accepted": "🟢",
            "draft": "🟡",
            "deprecated": "🟠",
            "superseded": "🔵",
            "archived": "⚪",
        }
        for status in status_order:
            adrs = status_groups.get(status)
            if not adrs:
                continue
            lines.append(
                f"## {status_icons.get(status, '⚪')} {status.capitalize()} ADRs"
            )
            lines.append("")
            lines.append(f"### {len(adrs)} decisions")
            lines.append("")
            for adr in adrs:
                self._append_adr_entry(
                    lines,
                    adr,
                    decision_link_prefix=decision_link_prefix,
                )

    def _append_adr_entry(
        self,
        lines: list[str],
        adr: ADRMetadata,
        *,
        decision_link_prefix: str,
    ) -> None:
        lines.append(f"### ADR-{adr.adr_number}: {adr.title}")
        lines.append("")
        lines.append(
            f"**Status**: `{adr.status}` | **Category**: `{adr.category}` | "
            f"**Owner**: `{adr.owner}`"
        )
        lines.append("")
        if adr.source_status and adr.source_status.lower() != adr.status.lower():
            lines.append(f"**Source status text**: `{adr.source_status}`")
            lines.append("")
        relationships = self._format_relationships(adr)
        if relationships:
            lines.append(f"**Relationships**: {relationships}")
            lines.append("")
        if adr.context:
            lines.append(f"**Context**: {adr.context[:150]}...")
            lines.append("")
        doc_path = f"{decision_link_prefix}/{adr.file_path}"
        lines.append(f"[📄 View Full ADR]({doc_path})")
        lines.append("")
        lines.append("---")
        lines.append("")

    @staticmethod
    def _format_relationships(adr: ADRMetadata) -> str:
        relationships = []
        if adr.supersedes:
            relationships.append(f"Supersedes: {', '.join(adr.supersedes)}")
        if adr.superseded_by:
            relationships.append(f"Superseded by: {', '.join(adr.superseded_by)}")
        if adr.related:
            relationships.append(f"Related: {', '.join(adr.related)}")
        return ", ".join(relationships)

    @staticmethod
    def _append_registry_footer(lines: list[str]) -> None:
        lines.append("## 🎯 Using the ADR Registry")
        lines.append("")
        lines.append(
            "- **Accepted ADRs**: Currently applicable architectural decisions"
        )
        lines.append("- **Draft ADRs**: Proposed decisions under review")
        lines.append(
            "- **Deprecated ADRs**: No longer recommended but may still be in use"
        )
        lines.append("- **Superseded ADRs**: Replaced by newer decisions")
        lines.append("- **Archived ADRs**: Historical decisions no longer relevant")
        lines.append("")
        lines.append("## 📋 ADR Lifecycle")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph LR")
        lines.append("    A[Draft] --> B[Accepted]")
        lines.append("    B --> C[Deprecated]")
        lines.append("    B --> D[Superseded]")
        lines.append("    C --> E[Archived]")
        lines.append("    D --> E[Archived]")
        lines.append("```")

    def generate_status_dashboard(self) -> str:
        """Generate a status dashboard for quick overview."""

        if not self.adrs:
            return "# ADR Status Dashboard\n\nNo ADRs found."

        # Count by status
        status_counts: dict[str, int] = {}
        for adr in self.adrs:
            status_counts[adr.status] = status_counts.get(adr.status, 0) + 1

        # Count by category
        category_counts: dict[str, int] = {}
        for adr in self.adrs:
            category_counts[adr.category] = category_counts.get(adr.category, 0) + 1

        lines = []
        lines.append("# 📊 ADR Status Dashboard")
        lines.append("")
        lines.append("Quick overview of ADR status and distribution.")
        lines.append("")
        lines.append(
            f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("")

        # Status distribution
        lines.append("## 📈 Status Distribution")
        lines.append("")
        lines.append("| Status | Count | Percentage |")
        lines.append("|--------|-------|------------|")

        for status in sorted(status_counts.keys()):
            count = status_counts[status]
            percentage = count / len(self.adrs) * 100
            lines.append(f"| `{status}` | {count} | {percentage:.1f}% |")

        lines.append("")

        # Category distribution
        lines.append("## 🏷️  Category Distribution")
        lines.append("")
        lines.append("| Category | Count | Percentage |")
        lines.append("|----------|-------|------------|")

        for category in sorted(category_counts.keys()):
            count = category_counts[category]
            percentage = count / len(self.adrs) * 100
            lines.append(f"| `{category}` | {count} | {percentage:.1f}% |")

        lines.append("")

        # Recent activity
        lines.append("## 🕒 Recent Activity")
        lines.append("")
        lines.append("Last 5 updated ADRs:")
        lines.append("")

        # Sort by last-reviewed date first, then decision date.
        recent_adrs = sorted(
            self.adrs,
            key=lambda x: max(
                self._parse_sortable_date(x.last_reviewed),
                self._parse_sortable_date(x.decision_date),
            ),
            reverse=True,
        )[:5]

        for adr in recent_adrs:
            date = adr.last_reviewed or adr.decision_date or "Unknown"
            lines.append(f"- **ADR-{adr.adr_number}**: {adr.title} ({date})")

        lines.append("")
        lines.append("## 🎯 Health Metrics")
        lines.append("")

        active_count = status_counts.get("accepted", 0)
        total_count = len(self.adrs)
        active_percentage = (active_count / total_count * 100) if total_count > 0 else 0

        lines.append(
            f"- **Accepted ADRs**: {active_count}/{total_count} ({active_percentage:.1f}%)"
        )
        lines.append(
            f"- **Maintenance Ratio**: {active_count}:{total_count - active_count}"
        )
        lines.append(
            f"- **Average ADRs/Year**: {total_count / 3:.1f} (assuming 3-year project)"
        )

        return "\n".join(lines)

    def generate_json_registry(self) -> ADRJsonRegistry:
        """Generate JSON registry for programmatic access."""

        adrs: list[ADRJsonRegistryEntry] = []
        status_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}

        for adr in self.adrs:
            adr_dict: ADRJsonRegistryEntry = {
                "adr_number": adr.adr_number,
                "title": adr.title,
                "file_path": adr.file_path,
                "status": adr.status,
                "source_status": adr.source_status,
                "category": adr.category,
                "owner": adr.owner,
                "decision_date": adr.decision_date,
                "last_reviewed": adr.last_reviewed,
                "context": adr.context,
                "decision": adr.decision,
                "consequences": adr.consequences,
                "supersedes": adr.supersedes,
                "superseded_by": adr.superseded_by,
                "related": adr.related,
                "tags": adr.tags,
            }

            adrs.append(adr_dict)

            status_counts[adr.status] = status_counts.get(adr.status, 0) + 1
            category_counts[adr.category] = category_counts.get(adr.category, 0) + 1

        return {
            "generated": datetime.now().isoformat(),
            "total_adrs": len(self.adrs),
            "adrs": adrs,
            "stats": {
                "by_status": status_counts,
                "by_category": category_counts,
            },
        }

    def write_output_files(self) -> None:
        """Write all output files to the registry directory."""

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate registry
        self.generate_adr_registry()

        if not self.adrs:
            print("⚠️  No ADRs to process")
            return

        # Write main registry index
        index_content = self.generate_registry_index(
            decision_link_prefix="../decisions"
        )
        index_file = self.output_dir / "index.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"✅ Written ADR registry index: {index_file}")

        # Write navigator-facing single-file registry used from Project Map.
        navigator_content = self.generate_registry_index(
            decision_link_prefix="decisions"
        )
        with open(self.navigator_registry_file, "w", encoding="utf-8") as f:
            f.write(navigator_content)
        print(f"✅ Written navigator ADR registry: {self.navigator_registry_file}")

        # Write status dashboard
        dashboard_content = self.generate_status_dashboard()
        dashboard_file = self.output_dir / "status-dashboard.md"
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
        print(f"✅ Written status dashboard: {dashboard_file}")

        # Write JSON registry
        json_registry = self.generate_json_registry()
        json_file = self.output_dir / "registry.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_registry, f, indent=2, ensure_ascii=False)
        print(f"✅ Written JSON registry: {json_file}")

        # Write README for the registry
        readme_content = self._generate_registry_readme()
        readme_file = self.output_dir / "README.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"✅ Written registry README: {readme_file}")

    def _generate_registry_readme(self) -> str:
        """Generate README for the ADR registry directory."""

        return """# ADR Registry

This directory contains the generated Architecture Decision Record (ADR) registry
with metadata, status tracking, and navigation aids.

## Authority

- `docs/02-architecture/decisions/README.md` is the canonical live ADR index.
- `index.md`, `status-dashboard.md`, and `registry.json` in this directory are
  generated mirrors for navigation and tooling.
- Regenerate these files with `python3 scripts/generate_adr_registry.py`
  whenever ADR files or ADR index metadata change.

## Files

- `index.md` - Main ADR registry with all decisions organized by status
- `status-dashboard.md` - Quick overview of ADR health and metrics
- `registry.json` - Machine-readable JSON registry for tooling integration

## Usage

### For Developers

1. **Browse ADRs**: Start with `index.md` for the complete registry
2. **Check Status**: Use `status-dashboard.md` for health metrics
3. **Find Decisions**: Use browser search (Ctrl+F) to find relevant ADRs
4. **Understand Context**: Each ADR entry includes context and relationships

### For Tooling

The `registry.json` file provides machine-readable access to all ADR metadata:

```json
{
  "generated": "2024-04-23T12:00:00",
  "total_adrs": 50,
  "adrs": [
    {
      "adr_number": "001",
      "title": "Decision Title",
      "status": "accepted",
      "source_status": "Accepted",
      "category": "architecture",
      "owner": "architecture-team",
      "file_path": "ADR-001-decision-title.md",
      "supersedes": [],
      "superseded_by": [],
      "related": []
    }
  ],
  "stats": {
    "by_status": {"accepted": 40, "deprecated": 5, "archived": 5},
    "by_category": {"architecture": 30, "data": 10, "infrastructure": 10}
  }
}
```

## ADR Lifecycle

```mermaid
graph LR
    A[Draft] --> B[Accepted]
    B --> C[Deprecated]
    B --> D[Superseded]
    C --> E[Archived]
    D --> E[Archived]
```

## Status Definitions

- **🟢 Accepted**: Currently applicable architectural decision
- **🟡 Draft**: Proposed decision under review
- **🟠 Deprecated**: No longer recommended but may still be in use
- **🔵 Superseded**: Replaced by a newer decision
- **⚪ Archived**: Historical decision no longer relevant

## Maintenance

This registry is automatically generated by `scripts/generate_adr_registry.py`.

To regenerate:

```bash
python3 scripts/generate_adr_registry.py
```

The registry should be regenerated whenever:
- New ADRs are added
- Existing ADRs are updated
- ADR status changes
- Before major releases

## Integration

The ADR registry integrates with:

1. **Project Navigator**: Linked from main documentation index
2. **CI/CD Pipeline**: Automated generation on documentation builds
3. **Architecture Reviews**: Used for ADR health monitoring
4. **Onboarding**: Helps new team members understand architectural context

## Related

- [ADR Decisions Directory](../decisions/)
- [Architecture Overview](../00-overview.md)
- [D-01 Documentation Governance](../../00-project/governance/01-documentation-governance-style-guide.md)
"""


def main() -> None:
    """Main entry point."""

    print("🚀 Generating ADR Registry...")
    print("=" * 50)

    generator = ADRRegistryGenerator()

    # Generate and write all output files
    generator.write_output_files()

    print("\n" + "=" * 50)
    print("✅ ADR Registry generation complete!")
    print("")
    print("📋 Summary:")
    print(f"   - Found {len(generator.adrs)} ADRs")
    print(f"   - Generated registry in {generator.output_dir}")
    print("   - Created index, dashboard, and JSON registry")
    print("")
    print("🎯 Next steps:")
    print("   1. Review the generated registry")
    print("   2. Integrate with project navigator")
    print("   3. Set up automated regeneration in CI/CD")
    print("   4. Update documentation governance with ADR processes")


if __name__ == "__main__":
    main()
