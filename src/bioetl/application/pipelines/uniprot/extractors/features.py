"""Feature extraction for UniProt records."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from bioetl.application.pipelines.uniprot.extractors.utils import clean_text


class FeatureExtractor:
    """Extracts feature-related data from UniProt XML records."""

    PTM_PATTERNS = [
        r"phospho",
        r"acetyl",
        r"methyl",
        r"ubiquitin",
        r"sumo",
        r"glycosyl",
        r"palmitoyl",
        r"myristoyl",
        r"farnesyl",
        r"geranyl",
    ]

    def _clean_text(self, text: str) -> str:
        """Removes trailing periods and excessive whitespace from text."""
        return clean_text(text)

    def extract_features(self, entry: ET.Element, ns: dict[str, str]) -> dict[str, Any]:
        """
        Extracts features from the UniProt entry.

        Args:
            entry: XML element for the entry
            ns: Namespace dictionary

        Returns:
            Dictionary of extracted features
        """
        features = entry.findall("u:feature", ns)

        extracted_features: dict[str, list[dict[str, Any]]] = {
            "binding_sites": [],
            "active_sites": [],
            "ptms": [],
            "variants": [],
            "mutagenesis": [],
            "transmembrane": [],
            "signal_peptide": [],
            "topological_domain": [],
        }

        for feature in features:
            f_type = feature.get("type")
            description = feature.get("description", "")

            # Extract location
            location = feature.find("u:location", ns)
            start = None
            end = None

            if location is not None:
                begin_elem = location.find("u:begin", ns)
                end_elem = location.find("u:end", ns)
                pos_elem = location.find("u:position", ns)

                if begin_elem is not None:
                    start = begin_elem.get("position")
                if end_elem is not None:
                    end = end_elem.get("position")
                if pos_elem is not None:
                    start = pos_elem.get("position")
                    end = start

            feature_data = {
                "description": self._clean_text(description),
                "start": start,
                "end": end,
                "original": None,
                "variation": None,
            }

            # Extract variation data if available
            original = feature.find("u:original", ns)
            variation = feature.find("u:variation", ns)

            if original is not None and original.text:
                feature_data["original"] = original.text
            if variation is not None and variation.text:
                feature_data["variation"] = variation.text

            if f_type == "binding site":
                extracted_features["binding_sites"].append(feature_data)
            elif f_type == "active site":
                extracted_features["active_sites"].append(feature_data)
            elif f_type == "modified residue":
                if self.extract_ptm_by_pattern(description):
                    extracted_features["ptms"].append(feature_data)
            elif f_type == "sequence variant":
                extracted_features["variants"].append(feature_data)
            elif f_type == "mutagenesis site":
                extracted_features["mutagenesis"].append(feature_data)
            elif f_type == "transmembrane region":
                extracted_features["transmembrane"].append(feature_data)
            elif f_type == "signal peptide":
                extracted_features["signal_peptide"].append(feature_data)
            elif f_type == "topological domain":
                extracted_features["topological_domain"].append(feature_data)

        return extracted_features

    def extract_ptm_by_pattern(self, description: str) -> bool:
        """Check if description matches any PTM pattern."""
        description = clean_text(description)
        if not description:
            return False

        # Check against patterns
        for pattern in self.PTM_PATTERNS:
            if re.search(pattern, description, re.IGNORECASE):
                return True

        return False
