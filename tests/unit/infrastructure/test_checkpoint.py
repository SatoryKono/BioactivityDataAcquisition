"""Unit tests for checkpointing."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from botocore.exceptions import ClientError

from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked S3 client."""
    with patch("bioetl.infrastructure.checkpoint.s3_checkpoint.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_s3
        mock_boto3.session.Config.return_value = MagicMock()
        yield mock_s3


@pytest.mark.unit
class TestS3Checkpoint:
    """Test S3Checkpoint functionality."""

    def test_s3_checkpoint_initialization(self, mock_s3_client):
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
        # Mock head_object to return no existing checkpoint
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        watermark = Watermark(datetime(2023, 1, 1, tzinfo=timezone.utc))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        metadata = {"key": "value"}

        cp.save(pipeline, watermark, run_id, metadata)

        expected_key = "checkpoints/test_pipeline/latest.json"
        mock_s3_client.put_object.assert_called_once()
        args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == expected_key
        # Body is a JSON string
        body = kwargs["Body"].decode("utf-8")
        assert "2023-01-01T00:00:00" in body
        assert "12345678-1234-5678-1234-567812345678" in body

    def test_load_returns_correct_data(self, mock_s3_client):
        """Test that load returns the correct data."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        json_body = b'{"watermark": "2023-01-01T00:00:00+00:00", "run_id": "12345678-1234-5678-1234-567812345678", "metadata": {}}'
        mock_body = MagicMock()
        mock_body.read.return_value = json_body
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = cp.load(pipeline)

        assert result is not None
        watermark, run_id, metadata = result
        # Watermark is returned as a proper Watermark type
        assert isinstance(watermark, datetime)
        assert run_id == RunID(UUID("12345678-1234-5678-1234-567812345678"))

    def test_load_nonexistent_checkpoint_returns_none(self, mock_s3_client):
        """Test that loading a nonexistent checkpoint returns None."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        result = cp.load(pipeline)

        assert result is None

    def test_delete_calls_s3_delete_object(self, mock_s3_client):
        """Test that delete calls s3:deleteObject."""
        cp = S3Checkpoint(bucket="test-bucket")
        pipeline = "test_pipeline"

        cp.delete(pipeline)

        expected_key = "checkpoints/test_pipeline/latest.json"
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key=expected_key
        )
