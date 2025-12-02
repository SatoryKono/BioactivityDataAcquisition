import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd
from pathlib import Path

from bioetl.application.pipelines.chembl.activity.extract import extract_activity
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig, ChemblSourceParameters

@pytest.fixture
def source_config():
    return ChemblSourceConfig(
        parameters=ChemblSourceParameters(base_url="https://test.com"),
        batch_size=100
    )

@pytest.fixture
def mock_config(source_config):
    config = MagicMock(spec=PipelineConfig)
    config.cli = {}
    config.pipeline = {}
    # Inject source config
    config.sources = {"chembl": source_config}
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

def test_extract_batch_size_from_config(mock_config, mock_service, tmp_path):
    """
    Test that batch_size from config controls chunking.
    We set batch_size=2 and provide 5 IDs, expecting 3 batches (2, 2, 1).
    """
    csv_path = tmp_path / "activity_batch_test.csv"
    ids = [1, 2, 3, 4, 5]
    pd.DataFrame({"activity_id": ids}).to_csv(csv_path, index=False)
    
    mock_config.cli = {"input_file": str(csv_path)}
    # Override batch size in source config
    mock_config.sources["chembl"].batch_size = 2
    
    with patch("bioetl.application.pipelines.chembl.activity.extract.ChemblResponseParser") as MockParser:
        parser_instance = MockParser.return_value
        parser_instance.parse.return_value = [] # Return empty for simplicity
        
        extract_activity(mock_config, mock_service)
        
        # Expect 3 calls: [1,2], [3,4], [5]
        assert mock_service.client.request_activity.call_count == 3
        
        calls = mock_service.client.request_activity.call_args_list
        assert calls[0][1]["activity_id__in"] == "1,2"
        assert calls[1][1]["activity_id__in"] == "3,4"
        assert calls[2][1]["activity_id__in"] == "5"

def test_extract_missing_column(mock_config, mock_service, tmp_path):
    """Test validation error when ID column is missing."""
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"wrong_col": [1]}).to_csv(csv_path, index=False)
    
    mock_config.cli = {"input_file": str(csv_path)}
    
    with pytest.raises(ValueError, match="must contain 'activity_id'"):
        extract_activity(mock_config, mock_service)
