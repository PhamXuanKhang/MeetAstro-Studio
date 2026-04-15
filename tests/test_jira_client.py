"""Tests cho JiraClient — mock requests.post, test stub mode."""
from unittest.mock import MagicMock, patch

import pytest
from requests.auth import HTTPBasicAuth

from src.modules.jira_client import JiraClient, _STUB_KEY
from src.schema import Epic, Priority, Subtask, Task


def make_epic() -> Epic:
    return Epic("Ra mắt Q1", "Chuẩn bị launch Q1.")


def make_task() -> Task:
    return Task("Triển khai", "Alice", "2024-01-15", Priority.HIGH, "context")


def make_subtask() -> Subtask:
    return Subtask("Cài môi trường", "Nam", "2024-01-10", Priority.MEDIUM, "context")


class TestJiraClientStubMode:
    def test_stub_when_no_credentials(self):
        client = JiraClient(base_url="", token="", project_key="")
        assert client.is_stub is True

    def test_stub_when_partial_credentials(self):
        client = JiraClient(base_url="https://jira.example.com", token="", project_key="")
        assert client.is_stub is True

    def test_create_epic_returns_stub_key(self):
        client = JiraClient(base_url="", token="", project_key="")
        result = client.create_epic(make_epic())
        assert result == _STUB_KEY

    def test_create_task_returns_stub_key(self):
        client = JiraClient(base_url="", token="", project_key="")
        result = client.create_task(make_task(), "EPIC-1")
        assert result == _STUB_KEY

    def test_create_subtask_returns_stub_key(self):
        client = JiraClient(base_url="", token="", project_key="")
        result = client.create_subtask(make_subtask(), "TASK-1")
        assert result == _STUB_KEY

    def test_stub_does_not_call_requests(self):
        client = JiraClient(base_url="", token="", project_key="")
        with patch("src.modules.jira_client.requests.post") as mock_post:
            client.create_epic(make_epic())
            client.create_task(make_task(), "EPIC-1")
            client.create_subtask(make_subtask(), "TASK-1")
        mock_post.assert_not_called()


class TestJiraClientRealMode:
    def _make_client(self) -> JiraClient:
        return JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            token="test-token",
            project_key="TEST",
        )

    def _mock_post_response(self, key: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": key}
        mock_resp.raise_for_status.return_value = None
        mock_resp.ok = True
        return mock_resp

    def test_not_stub_with_full_credentials(self):
        client = self._make_client()
        assert client.is_stub is False

    def test_create_epic_posts_to_jira(self):
        client = self._make_client()
        with patch("src.modules.jira_client.requests.post",
                   return_value=self._mock_post_response("TEST-1")) as mock_post:
            key = client.create_epic(make_epic())

        assert key == "TEST-1"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "rest/api/3/issue" in call_kwargs.args[0]

    def test_create_epic_payload_has_correct_fields(self):
        client = self._make_client()
        with patch("src.modules.jira_client.requests.post",
                   return_value=self._mock_post_response("TEST-1")) as mock_post:
            client.create_epic(make_epic())

        payload = mock_post.call_args.kwargs["json"]
        fields = payload["fields"]
        assert fields["summary"] == "Ra mắt Q1"
        assert fields["issuetype"]["name"] == "Epic"
        assert fields["project"]["key"] == "TEST"

    def test_create_task_sends_epic_link(self):
        client = self._make_client()
        with patch("src.modules.jira_client.requests.post",
                   return_value=self._mock_post_response("TEST-2")) as mock_post:
            client.create_task(make_task(), "TEST-1")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["fields"]["customfield_10014"] == "TEST-1"

    def test_create_task_sends_auth_header(self):
        client = self._make_client()
        with patch("src.modules.jira_client.requests.post",
                   return_value=self._mock_post_response("TEST-2")) as mock_post:
            client.create_task(make_task(), "TEST-1")

        auth = mock_post.call_args.kwargs["auth"]
        assert isinstance(auth, HTTPBasicAuth)
        assert auth.username == "test@example.com"
        assert auth.password == "test-token"

    def test_create_epic_logs_http_error_details(self, caplog):
        client = self._make_client()
        mock_resp = self._mock_post_response("TEST-4")
        mock_resp.ok = False
        mock_resp.status_code = 400
        mock_resp.text = '{"errorMessages":["Invalid custom field"]}'
        mock_resp.raise_for_status.side_effect = Exception("400 Client Error")

        with patch("src.modules.jira_client.requests.post", return_value=mock_resp):
            with caplog.at_level("ERROR"):
                with pytest.raises(Exception):
                    client.create_epic(make_epic())

        assert "Jira API trả về lỗi 400" in caplog.text
        assert "Invalid custom field" in caplog.text

    def test_create_subtask_sends_parent_key(self):
        client = self._make_client()
        with patch("src.modules.jira_client.requests.post",
                   return_value=self._mock_post_response("TEST-3")) as mock_post:
            client.create_subtask(make_subtask(), "TEST-2")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["fields"]["parent"]["key"] == "TEST-2"
        assert payload["fields"]["issuetype"]["name"] == "Subtask"
