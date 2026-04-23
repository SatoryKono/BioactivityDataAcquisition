#!/usr/bin/env python3
"""
Documentation Parity Check Script

Validates that documentation stays in sync with code and configuration.
Implements the parity gate requirements from the governance framework.
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import csv
from dataclasses import dataclass
import toml


@dataclass
class ParityResult:
    """Result of a parity check."""
    total_checked: int
    matches: int
    mismatches: int
    missing_docs: List[str]
    missing_code: List[str]
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
    doc_path: Optional[str] = None


class DocumentationParityChecker:
    """Main class for checking documentation parity."""
    
    def __init__(self):
        self.configs_dir = Path("configs")
        self.docs_dir = Path("docs")
        self.pipeline_specs_dir = self.docs_dir / "04-reference" / "pipeline-specs"
        self.entity_configs_dir = self.configs_dir / "entities"
        self.composite_configs_dir = self.configs_dir / "composites"
        
    def find_config_files(self) -> List[ConfigEntity]:
        """Find all configuration files that should have documentation."""
        
        config_entities = []
        
        # Entity configs
        if self.entity_configs_dir.exists():
            for config_file in self.entity_configs_dir.glob("*.yaml"):
                entity_name = config_file.stem
                config_entities.append(ConfigEntity(
                    name=entity_name,
                    type="entity",
                    path=str(config_file.relative_to(self.configs_dir))
                ))
        
        # Composite configs
        if self.composite_configs_dir.exists():
            for config_file in self.composite_configs_dir.glob("*.yaml"):
                composite_name = config_file.stem
                config_entities.append(ConfigEntity(
                    name=composite_name,
                    type="composite",
                    path=str(config_file.relative_to(self.configs_dir))
                ))
        
        return config_entities
    
    def find_documentation_files(self) -> List[Path]:
        """Find all pipeline specification documentation files."""
        
        doc_files = []
        
        if self.pipeline_specs_dir.exists():
            doc_files.extend(self.pipeline_specs_dir.glob("*.md"))
        
        # Also check for entity docs in reference section
        entity_docs_dir = self.docs_dir / "04-reference" / "entity-specs"
        if entity_docs_dir.exists():
            doc_files.extend(entity_docs_dir.glob("*.md"))
        
        return doc_files
    
    def extract_config_metadata(self, config_path: Path) -> Dict[str, str]:
        """Extract metadata from a configuration file."""
        
        try:
            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            elif config_path.suffix == ".toml":
                with open(config_path, 'r', encoding='utf-8') as f:
                    return toml.load(f)
            elif config_path.suffix == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"⚠️  Error reading config {config_path}: {e}")
            return {}
    
    def extract_doc_metadata(self, doc_path: Path) -> Dict[str, str]:
        """Extract metadata from a documentation file."""
        
        metadata = {
            'title': '',
            'description': '',
            'entity': '',
            'type': '',
            'status': 'active'
        }
        
        try:
            content = doc_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Check for front matter
            if content.startswith('---'):
                front_matter_end = content.find('\n---', 1)
                if front_matter_end != -1:
                    front_matter = content[3:front_matter_end].strip()
                    try:
                        metadata.update(yaml.safe_load(front_matter) or {})
                    except Exception as e:
                        print(f"⚠️  Error parsing front matter in {doc_path}: {e}")
            
            # Extract title from first header if no front matter
            if not metadata.get('title'):
                for line in lines:
                    if line.startswith('# '):
                        metadata['title'] = line[2:].strip()
                        break
            
            # Try to extract entity name from title or content
            if not metadata.get('entity'):
                title = metadata.get('title', '').lower()
                if 'entity' in title or 'pipeline' in title:
                    # Extract name from title like "Entity: molecule" or "Pipeline: activity"
                    parts = title.split(':')
                    if len(parts) > 1:
                        metadata['entity'] = parts[1].strip()
                else:
                    # Try to extract from filename
                    entity_name = doc_path.stem.replace('-spec', '').replace('pipeline-', '')
                    metadata['entity'] = entity_name
            
            return metadata
            
        except Exception as e:
            print(f"⚠️  Error reading doc {doc_path}: {e}")
            return metadata
    
    def match_configs_to_docs(self, configs: List[ConfigEntity]) -> List[ConfigEntity]:
        """Match configuration entities to their documentation."""
        
        doc_files = self.find_documentation_files()
        doc_metadata_cache = {}
        
        # Build documentation metadata cache
        for doc_file in doc_files:
            metadata = self.extract_doc_metadata(doc_file)
            entity_name = metadata.get('entity', '').lower()
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
                parity_percentage=100.0
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
            entity = metadata.get('entity', '')
            if entity:
                doc_entities.add(entity.lower())
        
        config_entities = {config.name.lower() for config in matched_configs}
        missing_code = [
            f"doc:{entity}"
            for entity in doc_entities - config_entities
        ]
        
        parity_percentage = (matches / len(matched_configs) * 100) if matched_configs else 100.0
        
        return ParityResult(
            total_checked=len(matched_configs),
            matches=matches,
            mismatches=mismatches,
            missing_docs=missing_docs,
            missing_code=list(missing_code),
            parity_percentage=parity_percentage
        )
    
    def generate_report(self, result: ParityResult) -> str:
        """Generate a detailed parity report."""
        
        report = []
        report.append("# 📊 Documentation Parity Report")
        report.append("")
        report.append(f"**Generated**: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")
        report.append(f"**Total Configs Checked**: {result.total_checked}")
        report.append(f"**Documentation Coverage**: {result.matches}/{result.total_checked} ({result.parity_percentage:.1f}%)")
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
            report.append("- 🔴 **CRITICAL**: Merge blocked due to missing documentation")
            report.append("- Create documentation for all missing configurations before merging")
            report.append("- Consider removing orphaned documentation or linking to active configs")
        elif result.is_error():
            report.append("- 🟡 **ERROR**: Documentation parity below acceptable threshold")
            report.append("- Prioritize creating documentation for missing configurations")
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
    
    def generate_json_report(self, result: ParityResult) -> Dict:
        """Generate a JSON report for CI/CD integration."""
        
        return {
            "timestamp": subprocess.run(['date', '--iso-8601=seconds'], capture_output=True, text=True).stdout.strip(),
            "metrics": {
                "total_checked": result.total_checked,
                "matches": result.matches,
                "mismatches": result.mismatches,
                "parity_percentage": result.parity_percentage,
                "missing_docs_count": len(result.missing_docs),
                "missing_code_count": len(result.missing_code)
            },
            "status": "critical" if result.is_critical() else "error" if result.is_error() else "warning" if result.is_warning() else "pass",
            "missing_docs": result.missing_docs,
            "missing_code": result.missing_code,
            "thresholds": {
                "block": 85.0,
                "error": 90.0,
                "warning": 95.0,
                "pass": 95.0
            }
        }


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
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2)
    
    print(f"\n📊 JSON report written to: {report_file}")
    
    # Exit with appropriate code
    if result.is_critical():
        print("\n❌ CRITICAL: Documentation parity requirements not met - merge blocked")
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