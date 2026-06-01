"""Unit tests for UniProt FeatureExtractor."""

import pytest

import json
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor


pytestmark = pytest.mark.unit

class TestFeatureExtractor:
    """Tests for FeatureExtractor class."""

    def test_extract_features_valid(self):
        """Test extraction of valid features list."""
        features = [
            {
                "type": "Domain",
                "description": "Test Domain",
                "location": {"start": {"value": 10}, "end": {"value": 20}},
            }
        ]
        result = FeatureExtractor.extract_features(features)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["type"] == "Domain"
        assert parsed[0]["description"] == "Test Domain"
        assert parsed[0]["start"] == 10
        assert parsed[0]["end"] == 20

    def test_extract_features_empty(self):
        """Test extraction with empty features list."""
        assert FeatureExtractor.extract_features([]) is None
        assert FeatureExtractor.extract_features(None) is None

    def test_extract_features_invalid_structure(self):
        """Test extraction with invalid feature objects."""
        features = ["not-a-dict", {"type": "Domain"}]
        result = FeatureExtractor.extract_features(features)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["type"] == "Domain"

    def test_feature_extractor__extract_keywords__75228603(self):
        """Test keyword extraction."""
        keywords = [
            {"id": "KW-0001", "name": "Keyword 1", "category": "Biological process"},
            {"id": "KW-0002", "name": "Keyword 2"},
        ]
        result = FeatureExtractor.extract_keywords(keywords)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "KW-0001"
        assert parsed[0]["category"] == "Biological process"
        assert parsed[1]["name"] == "Keyword 2"

    def test_feature_extractor__keywords_empty__e7d3da4d(self):
        """Test keyword extraction with empty list."""
        assert FeatureExtractor.extract_keywords([]) is None
        assert FeatureExtractor.extract_keywords(None) is None

    def test_extract_features_by_type(self):
        """Test extraction by specific feature type."""
        features = [
            {"type": "Domain", "description": "Keep me"},
            {"type": "Region", "description": "Ignore me"},
        ]
        result = FeatureExtractor.extract_features_by_type(features, "Domain")
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["description"] == "Keep me"

    def test_extract_domains(self):
        """Test domain extraction helper."""
        features = [{"type": "Domain", "description": "Test Domain"}]
        result = FeatureExtractor.extract_domains(features)
        assert result is not None
        assert "Test Domain" in result

    def test_extract_binding_sites(self):
        """Test binding site extraction helper."""
        features = [{"type": "Binding site", "description": "ATP"}]
        result = FeatureExtractor.extract_binding_sites(features)
        assert result is not None
        assert "ATP" in result

    def test_extract_active_sites(self):
        """Test active site extraction helper."""
        features = [{"type": "Active site", "description": "Proton donor"}]
        result = FeatureExtractor.extract_active_sites(features)
        assert result is not None
        assert "Proton donor" in result

    def test_extract_topology(self):
        """Test topology extraction helper."""
        features = [{"type": "Topological domain", "description": "Cytoplasmic"}]
        result = FeatureExtractor.extract_topology(features)
        assert result is not None
        assert "Cytoplasmic" in result

    def test_extract_transmembrane(self):
        """Test transmembrane extraction helper."""
        features = [{"type": "Transmembrane", "description": "Helical"}]
        result = FeatureExtractor.extract_transmembrane(features)
        assert result is not None
        assert "Helical" in result

    def test_extract_intramembrane(self):
        """Test intramembrane extraction helper."""
        features = [{"type": "Intramembrane", "description": "Region"}]
        result = FeatureExtractor.extract_intramembrane(features)
        assert result is not None
        assert "Region" in result

    def test_extract_glycosylation(self):
        """Test glycosylation extraction helper."""
        features = [{"type": "Glycosylation", "description": "N-linked"}]
        result = FeatureExtractor.extract_glycosylation(features)
        assert result is not None
        assert "N-linked" in result

    def test_extract_lipidation(self):
        """Test lipidation extraction helper."""
        features = [{"type": "Lipidation", "description": "Myristate"}]
        result = FeatureExtractor.extract_lipidation(features)
        assert result is not None
        assert "Myristate" in result

    def test_extract_disulfide_bonds(self):
        """Test disulfide bond extraction helper."""
        features = [{"type": "Disulfide bond", "description": "1-2"}]
        result = FeatureExtractor.extract_disulfide_bonds(features)
        assert result is not None
        assert "1-2" in result

    def test_extract_modified_residues(self):
        """Test modified residue extraction helper."""
        features = [{"type": "Modified residue", "description": "Phosphoserine"}]
        result = FeatureExtractor.extract_modified_residues(features)
        assert result is not None
        assert "Phosphoserine" in result

    def test_extract_signal_peptide(self):
        """Test signal peptide extraction helper."""
        features = [{"type": "Signal peptide", "description": "Signal"}]
        result = FeatureExtractor.extract_signal_peptide(features)
        assert result is not None
        assert "Signal" in result

    def test_extract_propeptide(self):
        """Test propeptide extraction helper."""
        features = [{"type": "Propeptide", "description": "Pro"}]
        result = FeatureExtractor.extract_propeptide(features)
        assert result is not None
        assert "Pro" in result

    def test_extract_ptm_by_pattern(self):
        """Test PTM extraction by pattern matching."""
        features = [
            {"type": "Modified residue", "description": "Phosphoserine"},
            {"type": "Modified residue", "description": "Acetylation"},
            {"type": "Other", "description": "Phosphoserine"},  # Wrong type
        ]

        # Test phosphorylation pattern
        result = FeatureExtractor.extract_phosphorylation(features)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["description"] == "Phosphoserine"

        # Test acetylation pattern
        result = FeatureExtractor.extract_acetylation(features)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["description"] == "Acetylation"

        # Test non-matching pattern
        result = FeatureExtractor.extract_ubiquitination(features)
        assert result is None

    def test_extract_ptm_by_pattern_direct(self):
        """Direct API test for extract_ptm_by_pattern."""
        features = [
            {"type": "Modified residue", "description": "Acetyllysine"},
            {"type": "Modified residue", "description": "Phosphoserine"},
            {"type": "Domain", "description": "Phospho-like name"},
        ]

        result = FeatureExtractor.extract_ptm_by_pattern(features, ("acetyl",))
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["description"] == "Acetyllysine"

        assert FeatureExtractor.extract_ptm_by_pattern(features, ()) is None

    def test_feature_location_parsing(self):
        """Test parsing of different location formats."""
        features = [
            {
                "type": "Domain",
                "location": {
                    "start": {"value": 10, "modifier": "EXACT"},
                    "end": {"value": 20, "modifier": "EXACT"},
                },
            },
            {
                "type": "Domain",
                "location": {
                    # Missing values
                    "start": {},
                    "end": {},
                },
            },
        ]
        result = FeatureExtractor.extract_features(features)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["start"] == 10
        assert parsed[0]["end"] == 20
        assert "start" not in parsed[1]
        assert "end" not in parsed[1]
