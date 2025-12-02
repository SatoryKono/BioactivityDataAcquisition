import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from pathlib import Path

from bioetl.application.pipelines.chembl.activity.extract import extract_activity
from bioetl.infrastructure.config.models import PipelineConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=PipelineConfig)
    config.cli = {}
    config.pipeline = {}
    return config

@pytest.fixture
def mock_service():
    service = MagicMock()
    service.extract_all.return_value = pd.DataFrame({"activity_id": [1, 2, 3]})
    service.client.request_activity.return_value = {"activities": [{"activity_id": 1}]}
    return service

def test_extract_no_input_file(mock_config, mock_service):
    """Test extraction falls back to default service when no input file is provided."""
    mock_config.cli = {}
    
    df = extract_activity(mock_config, mock_service)
    
    mock_service.extract_all.assert_called_once_with("activity")
    assert not df.empty
    assert "activity_id" in df.columns

def test_extract_full_data_csv(mock_config, mock_service, tmp_path):
    """Test extraction reads full dataframe from CSV."""
    csv_path = tmp_path / "activity.csv"
    pd.DataFrame({
        "activity_id": [10, 11],
        "standard_value": [5.5, 6.6],
        "standard_type": ["IC50", "Ki"]
    }).to_csv(csv_path, index=False)
    
    mock_config.cli = {"input_file": str(csv_path)}
    
    df = extract_activity(mock_config, mock_service)
    
    assert len(df) == 2
    assert "standard_value" in df.columns
    mock_service.extract_all.assert_not_called()
    mock_service.client.request_activity.assert_not_called()

def test_extract_ids_only_csv(mock_config, mock_service, tmp_path):
    """Test extraction fetches data by IDs when CSV contains only IDs."""
    csv_path = tmp_path / "activity_ids.csv"
    pd.DataFrame({
        "activity_id": [100, 101, 102]
    }).to_csv(csv_path, index=False)
    
    mock_config.cli = {"input_file": str(csv_path)}
    
    # Mock parser to return something
    with patch("bioetl.application.pipelines.chembl.activity.extract.ChemblResponseParser") as MockParser:
        parser_instance = MockParser.return_value
        parser_instance.parse.side_effect = [
            [{"activity_id": 100}, {"activity_id": 101}, {"activity_id": 102}]
        ]
        
        df = extract_activity(mock_config, mock_service)
        
        assert len(df) == 3
        # Verify batch request was made
        mock_service.client.request_activity.assert_called()
        # Verify call args contain the IDs
        call_kwargs = mock_service.client.request_activity.call_args[1]
        assert "activity_id__in" in call_kwargs
        assert "100" in call_kwargs["activity_id__in"]

def test_extract_missing_column(mock_config, mock_service, tmp_path):
    """Test validation error when ID column is missing."""
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"wrong_col": [1]}).to_csv(csv_path, index=False)
    
    mock_config.cli = {"input_file": str(csv_path)}
    
    with pytest.raises(ValueError, match="must contain 'activity_id'"):
        extract_activity(mock_config, mock_service)

