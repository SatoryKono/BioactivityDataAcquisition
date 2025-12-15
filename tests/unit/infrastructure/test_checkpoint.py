"""Unit tests for checkpointing."""

from unittest.mock import MagicMock, patch

import pytest

from uuid import UUID

from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked S3 client."""
    with patch("boto3.client") as mock_boto_client:
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        yield mock_s3


@pytest.mark.unit
class TestS3Checkpoint:
    """Test S3Checkpoint functionality."""

    def test_s3_checkpoint_initialization(self):
        """Test S3Checkpoint can be initialized."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        assert cp.bucket == "test-bucket"

    def test_save_generates_correct_key_and_body(self, mock_s3_client):
        """Test that save generates the correct S3 key and body."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        watermark = Watermark("2023-01-01T00:00:00Z")
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        metadata = {"key": "value"}

        cp.save(pipeline, watermark, run_id, metadata)

        expected_key = "test_pipeline.json"
        mock_s3_client.put_object.assert_called_once()
        args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == expected_key
        # Body is a JSON string, so we can't compare directly
        assert b'"watermark": "2023-01-01T00:00:00Z"' in kwargs["Body"]
        assert b'"run_id": "12345678-1234-5678-1234-567812345678"' in kwargs["Body"]

    def test_load_returns_correct_data(self, mock_s3_client):
        """Test that load returns the correct data."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        json_body = b'{"watermark": "2023-01-01T00:00:00Z", "run_id": "12345678-1234-5678-1234-567812345678", "metadata": {}}'
        mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: json_body)}

        watermark, run_id, metadata = cp.load(pipeline)

        assert watermark == "2023-01-01T00:00:00Z"
        assert run_id == "12345678-1234-5678-1234-567812345678"

    def test_load_nonexistent_checkpoint_returns_none(self, mock_s3_client):
        """Test that loading a nonexistent checkpoint returns None."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        mock_s3_client.get_object.side_effect = Exception("NoSuchKey")

        result = cp.load(pipeline)

        assert result is None

    def test_delete_calls_s3_delete_object(self, mock_s3_client):
        """Test that delete calls s3:deleteObject."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"

        cp.delete(pipeline)

        expected_key = "test_pipeline.json"
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key=expected_key
        )
