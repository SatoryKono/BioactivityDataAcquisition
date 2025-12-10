"""Tests for DataFlowConfig aggregate."""

import pytest

from bioetl.domain.configs.data_flow import DataFlowConfig
from bioetl.domain.configs.sink import DataSinkConfig
from bioetl.domain.configs.source import DataSourceConfig


class TestDataFlowConfig:
    """Tests for DataFlowConfig aggregate."""

    def test_creates_valid_data_flow(self) -> None:
        """DataFlowConfig can be created with valid source and sink."""
        source = DataSourceConfig(input_mode="csv", input_path="/tmp/input.csv")
        sink = DataSinkConfig(output_path="/tmp/output")

        data_flow = DataFlowConfig(source=source, sink=sink)

        assert data_flow.source.input_mode == "csv"
        assert data_flow.sink.output_path == "/tmp/output"

    def test_is_frozen(self) -> None:
        """DataFlowConfig is immutable."""
        source = DataSourceConfig(input_mode="csv", input_path="/tmp/input.csv")
        sink = DataSinkConfig(output_path="/tmp/output")
        data_flow = DataFlowConfig(source=source, sink=sink)

        with pytest.raises(Exception):  # Pydantic frozen model
            data_flow.source = DataSourceConfig(input_mode="id_only", input_path="/tmp/other.csv")

    def test_forbids_extra_fields(self) -> None:
        """DataFlowConfig rejects unknown fields."""
        source = DataSourceConfig(input_mode="csv", input_path="/tmp/input.csv")
        sink = DataSinkConfig(output_path="/tmp/output")

        with pytest.raises(Exception):
            DataFlowConfig(source=source, sink=sink, unknown_field="value")


class TestDataFlowValidation:
    """Tests for DataFlowConfig validation."""

    def test_rejects_same_input_output_path(self) -> None:
        """DataFlowConfig rejects when input and output paths are the same file."""
        source = DataSourceConfig(input_mode="csv", input_path="/tmp/data.csv")
        sink = DataSinkConfig(output_path="/tmp/data.csv")

        with pytest.raises(ValueError, match="Output path cannot be the same as input path"):
            DataFlowConfig(source=source, sink=sink)

    def test_allows_different_paths(self) -> None:
        """DataFlowConfig allows different input and output paths."""
        source = DataSourceConfig(input_mode="csv", input_path="/tmp/input.csv")
        sink = DataSinkConfig(output_path="/tmp/output.json")

        data_flow = DataFlowConfig(source=source, sink=sink)
        assert data_flow.source.input_path == "/tmp/input.csv"
        assert data_flow.sink.output_path == "/tmp/output.json"

    def test_allows_auto_detect_without_input_path(self) -> None:
        """DataFlowConfig allows auto_detect mode without input path."""
        source = DataSourceConfig(input_mode="auto_detect")
        sink = DataSinkConfig(output_path="/tmp/output")

        data_flow = DataFlowConfig(source=source, sink=sink)
        assert data_flow.source.input_mode == "auto_detect"
        assert data_flow.source.input_path is None

    def test_allows_output_to_different_directory(self) -> None:
        """DataFlowConfig allows output to a different directory than input."""
        source = DataSourceConfig(input_mode="csv", input_path="/data/input/file.csv")
        sink = DataSinkConfig(output_path="/data/output/")

        data_flow = DataFlowConfig(source=source, sink=sink)
        assert data_flow.source.input_path == "/data/input/file.csv"
        assert data_flow.sink.output_path == "/data/output"


class TestDataFlowFromDict:
    """Tests for DataFlowConfig creation from dict."""

    def test_creates_from_nested_dict(self) -> None:
        """DataFlowConfig can be created from nested dict."""
        data_flow = DataFlowConfig(
            source={
                "input_mode": "csv",
                "input_path": "/tmp/input.csv",
                "batch_size": 50,
            },
            sink={
                "output_path": "/tmp/output",
                "dry_run": True,
            },
        )

        assert data_flow.source.input_mode == "csv"
        assert data_flow.source.batch_size == 50
        assert data_flow.sink.dry_run is True

    def test_source_csv_options_work(self) -> None:
        """DataFlowConfig correctly handles CSV options in source."""
        data_flow = DataFlowConfig(
            source={
                "input_mode": "csv",
                "input_path": "/tmp/input.csv",
                "csv": {"delimiter": ";", "encoding": "utf-8"},
            },
            sink={"output_path": "/tmp/output"},
        )

        assert data_flow.source.csv.delimiter == ";"
        assert data_flow.source.csv.encoding == "utf-8"
