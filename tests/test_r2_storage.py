"""Tests for R2Storage backend with mocked boto3."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from tube_agent.storage.r2 import R2Storage


@pytest.fixture
def r2():
    with patch("tube_agent.storage.r2.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        storage = R2Storage(
            endpoint_url="https://r2.example.com",
            access_key="test-key",
            secret_key="test-secret",
            bucket="test-bucket",
        )
        yield storage, mock_client


class TestSaveChannel:
    def test_put_object_called_with_correct_key(self, r2):
        storage, mock_client = r2
        data = {"id": "UC123", "handle": "testchannel", "title": "Test"}

        storage.save_channel(data)

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "channels/testchannel/channel.json"
        body = json.loads(call_kwargs["Body"].decode("utf-8"))
        assert body["handle"] == "testchannel"

    def test_returns_channel_id(self, r2):
        storage, _ = r2
        result = storage.save_channel({"id": "UC123", "handle": "test"})
        assert result == "UC123"


class TestSaveVideos:
    def test_uploads_to_correct_key(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"
        videos = [{"videoId": "v1", "title": "Video 1"}]

        storage.save_videos("UC123", videos)

        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Key"] == "channels/testchannel/videos.json"
        body = json.loads(call_kwargs["Body"].decode("utf-8"))
        assert len(body) == 1
        assert body[0]["videoId"] == "v1"

    def test_empty_videos_skipped(self, r2):
        storage, mock_client = r2
        result = storage.save_videos("UC123", [])
        assert result == 0
        mock_client.put_object.assert_not_called()


class TestSaveReport:
    def test_uploads_markdown(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"

        storage.save_report("UC123", "comprehensive", "# Report\nContent here")

        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Key"] == "channels/testchannel/reports/comprehensive.md"
        assert call_kwargs["ContentType"] == "text/markdown"
        assert call_kwargs["Body"] == b"# Report\nContent here"


class TestGetChannel:
    def test_returns_parsed_json(self, r2):
        storage, mock_client = r2
        data = {"id": "UC123", "handle": "test", "title": "Test Channel"}
        mock_client.get_object.return_value = {
            "Body": BytesIO(json.dumps(data).encode("utf-8")),
        }

        result = storage.get_channel("test")

        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="channels/test/channel.json"
        )
        assert result == data

    def test_returns_none_when_not_found(self, r2):
        storage, mock_client = r2
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        result = storage.get_channel("nonexistent")
        assert result is None


class TestHasSummary:
    def test_returns_true_when_exists(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"
        mock_client.head_object.return_value = {}

        assert storage.has_summary("v1") is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="channels/testchannel/summaries/v1.json"
        )

    def test_returns_false_when_not_found(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}},
            "HeadObject",
        )

        assert storage.has_summary("v1") is False


class TestGetSummary:
    def test_returns_summary_data(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"
        summary = {"videoId": "v1", "title": "Test", "analysis": {"topics": ["tech"]}}
        mock_client.get_object.return_value = {
            "Body": BytesIO(json.dumps(summary).encode("utf-8")),
        }

        result = storage.get_summary("v1")
        assert result == summary

    def test_returns_none_when_not_found(self, r2):
        storage, mock_client = r2
        storage._channel_map["UC123"] = "testchannel"
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        result = storage.get_summary("v1")
        assert result is None


class TestJobs:
    def test_jobs_are_in_memory(self, r2):
        storage, _ = r2
        job_id = storage.create_job({"handle": "test", "type": "full"})
        job = storage.get_job(job_id)
        assert job["status"] == "pending"
        assert job["handle"] == "test"

        storage.update_job(job_id, {"status": "running"})
        assert storage.get_job(job_id)["status"] == "running"

    def test_get_nonexistent_job(self, r2):
        storage, _ = r2
        assert storage.get_job("nonexistent") is None
