#!/usr/bin/env python3
"""
Entity Config Parity Check Script

This script verifies that all active entity configurations have corresponding
pipeline specification documents and vice versa.

Usage:
    python3 scripts/check_entity_config_parity.py
    
Exit Codes:
    0: All checks passed
    1: Parity issues found
    2: Error during execution
"""

# Compatibility wrapper

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configuration paths
ENTITIES_DIR = Path("configs/entities")
PIPELINES_DIR = Path("docs/04-reference/pipelines")

FORBIDDEN_ACTIVE_SPEC_MARKERS = (
    "**status**: historical deep spec. current canonical contract lives in",
    "published-page role | pass | historical deep spec or summary is explicitly bounded by current canonical sources",
    "this document contains historical references. for the most current information",
    "do not copy field names or loading examples from this legacy page.",
    "treat this file as historical evidence, not as the current publication similarity contract.",
)

class ParityChecker:
    def __init__(self):
        self.entity_configs = self._load_entity_configs()
        self.pipeline_specs = self._load_pipeline_specs()
        self.issues = []

    @staticmethod
    def _normalize_text(content: str) -> str:
        """Collapse whitespace so multiline markdown markers can be matched reliably."""
        return " ".join(content.lower().split())
    
    def _load_entity_configs(self) -> Dict[Tuple[str, str], Path]:
        """Load all entity configuration files."""
        configs = {}
        
        if not ENTITIES_DIR.exists():
            print(f"Warning: {ENTITIES_DIR} does not exist")
            return configs
            
        for provider_dir in ENTITIES_DIR.iterdir():
            if not provider_dir.is_dir():
                continue
                
            provider = provider_dir.name
            for config_file in provider_dir.glob("*.yaml"):
                entity = config_file.stem
                configs[(provider, entity)] = config_file
        
        return configs
    
    def _load_pipeline_specs(self) -> Dict[Tuple[str, str], Path]:
        """Load all pipeline specification files."""
        specs = {}
        
        if not PIPELINES_DIR.exists():
            print(f"Warning: {PIPELINES_DIR} does not exist")
            return specs
            
        # Look for spec files in provider subdirectories
        for provider_dir in PIPELINES_DIR.iterdir():
            if not provider_dir.is_dir():
                continue
                
            provider = provider_dir.name
            for spec_file in provider_dir.glob("*spec.md"):
                # Extract entity from filename (e.g., "05-activity-spec.md" -> "activity")
                entity = spec_file.stem.replace("-spec", "").split("-")[-1]
                
                # Handle common naming mismatches
                entity_mapping = {
                    'class': 'protein_class',
                    'line': 'cell_line',
                    'parameters': 'assay_parameters',
                    'record': 'compound_record',
                    'component': 'target_component',
                    'term': 'publication_term',
                    'similarity': 'publication_similarity',
                    'fraction': 'subcellular_fraction'
                }
                
                # Use mapped name if available, otherwise use original
                mapped_entity = entity_mapping.get(entity, entity)
                specs[(provider, mapped_entity)] = spec_file
        
        return specs
    
    def _get_active_entities(self) -> Set[Tuple[str, str]]:
        """Get set of active entities from configs."""
        active = set()
        
        for (provider, entity), config_path in self.entity_configs.items():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                # Check if entity is active (not disabled)
                if config.get('status', 'active') != 'disabled':
                    active.add((provider, entity))
                    
            except Exception as e:
                self.issues.append(f"Error reading {config_path}: {e}")
        
        return active
    
    def check_config_to_spec_parity(self):
        """Check that all active entity configs have corresponding spec files."""
        active_entities = self._get_active_entities()
        
        print(f"Checking parity for {len(active_entities)} active entities...")
        
        for provider, entity in active_entities:
            if (provider, entity) not in self.pipeline_specs:
                self.issues.append(
                    f"Missing pipeline spec for {provider}/{entity}. "
                    f"Config exists at: {self.entity_configs[(provider, entity)]}"
                )
    
    def check_spec_to_config_parity(self):
        """Check that all pipeline specs have corresponding config files."""
        print(f"Checking {len(self.pipeline_specs)} pipeline specs...")
        
        for (provider, entity), spec_path in self.pipeline_specs.items():
            if (provider, entity) not in self.entity_configs:
                self.issues.append(
                    f"Missing entity config for {provider}/{entity}. "
                    f"Spec exists at: {spec_path}"
                )
    
    def check_spec_status(self):
        """Fail when active pipeline specs still self-identify as historical stubs."""
        print("Checking canonical status markers in pipeline specs...")

        for (provider, entity), spec_path in self.pipeline_specs.items():
            try:
                with open(spec_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                normalized_content = self._normalize_text(content)
                for marker in FORBIDDEN_ACTIVE_SPEC_MARKERS:
                    if marker in normalized_content:
                        self.issues.append(
                            "Active pipeline spec still advertises itself as a historical/legacy "
                            f"surface for {provider}/{entity}: {spec_path}"
                        )
                        break
            except Exception as e:
                self.issues.append(f"Error reading {spec_path}: {e}")
    
    def generate_report(self):
        """Generate a summary report."""
        print("\n" + "="*60)
        print("ENTITY CONFIG PARITY REPORT")
        print("="*60)
        
        print(f"\nEntity Configurations: {len(self.entity_configs)}")
        print(f"Pipeline Specifications: {len(self.pipeline_specs)}")
        print(f"Active Entities: {len(self._get_active_entities())}")
        
        # Calculate parity score
        active_entities = self._get_active_entities()
        parity_score = (len(active_entities) / max(len(self.entity_configs), 1)) * 100
        
        if self.issues:
            print(f"\n⚠️  Critical Issues Found: {len(self.issues)}")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
            print(f"\n📊 Parity Score: {parity_score:.1f}%")
            return False
        else:
            print(f"\n✅ All parity checks passed!")
            print(f"📊 Parity Score: {parity_score:.1f}%")
            if parity_score >= 95:
                print("🎉 Excellent documentation coverage!")
            return True
    
    def run(self) -> bool:
        """Run all parity checks."""
        try:
            self.check_config_to_spec_parity()
            self.check_spec_to_config_parity()
            self.check_spec_status()
            return self.generate_report()
        except Exception as e:
            print(f"Error during parity check: {e}")
            return False

if __name__ == "__main__":
    checker = ParityChecker()
    success = checker.run()
    
    # Exit with appropriate code
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
