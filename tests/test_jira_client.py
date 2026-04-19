"""Tests cho JiraClient — mock httpx.AsyncClient, test stub mode."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.jira_client import JiraClient, _STUB_KEY
from src.schema import Epic, Priority, Subtask, Task


def make_epic() -> Epic:
    return Epic(summary="Ra mắt Q1", description="Chuẩn bị launch Q1.")


def make_task() -> Task:
    return Task(summary="Triển khai", assignee="Alice", deadline="2024-01-15", priority=Priority.HIGH, context="context")


def make_subtask() -> Subtask:
    return Subtask(summary="Cài môi trường", assignee="Nam", deadline="2024-01-10", priority=Priority.MEDIUM, context="context")


def _mock_httpx_response(key: str, status_code: int = 200, body: dict = None) -> MagicMock:
    """Tạo mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = body if body is not None else {"key": key}
    mock_resp.text = ""
    return mock_resp


def _patch_httpx_post(key: str = "TEST-1", status_code: int = 200, body: dict = None):
    """Context manager patch httpx.AsyncClient.post."""
    mock_response = _mock_httpx_response(key, status_code, body)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return patch("src.modules.jira_client.httpx.AsyncClient", return_value=mock_client), mock_client


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

    def test_stub_does_not_call_httpx(self):
        client = JiraClient(base_url="", token="", project_key="")
        patcher, mock_client = _patch_httpx_post()
        with patcher:
            client.create_epic(make_epic())
            client.create_task(make_task(), "EPIC-1")
            client.create_subtask(make_subtask(), "TASK-1")
        mock_client.post.assert_not_called()


class TestJiraClientRealMode:
    def _make_client(self) -> JiraClient:
        return JiraClient(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            token="test-token",
            project_key="TEST",
        )

    def test_not_stub_with_full_credentials(self):
        client = self._make_client()
        assert client.is_stub is False

    def test_create_epic_posts_to_jira(self):
        client = self._make_client()
        patcher, mock_client = _patch_httpx_post("TEST-1")
        with patcher:
            key = client.create_epic(make_epic())

        assert key == "TEST-1"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "rest/api/3/issue" in call_args.args[0]

    def test_create_epic_payload_has_correct_fields(self):
        client = self._make_client()
        patcher, mock_client = _patch_httpx_post("TEST-1")
        with patcher:
            client.create_epic(make_epic())

        payload = mock_client.post.call_args.kwargs["json"]
        fields = payload["fields"]
        assert fields["summary"] == "Ra mắt Q1"
        assert fields["issuetype"]["name"] == "Epic"
        assert fields["project"]["key"] == "TEST"

    def test_create_task_sends_epic_link(self):
        client = self._make_client()
        patcher, mock_client = _patch_httpx_post("TEST-2")
        with patcher:
            client.create_task(make_task(), "TEST-1")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["fields"]["customfield_10014"] == "TEST-1"

    def test_create_task_sends_auth(self):
        client = self._make_client()
        patcher, mock_client = _patch_httpx_post("TEST-2")
        with patcher:
            client.create_task(make_task(), "TEST-1")

        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["auth"] == ("test@example.com", "test-token")

    def test_create_epic_logs_http_error_details(self, caplog):
        client = self._make_client()
        error_body = {"errorMessages": ["Invalid custom field"], "errors": {}}
        patcher, _ = _patch_httpx_post("TEST-4", status_code=400, body=error_body)
        with patcher:
            with caplog.at_level("ERROR"):
                with pytest.raises(RuntimeError):
                    client.create_epic(make_epic())

        assert "Jira API trả về lỗi 400" in caplog.text
        assert "Invalid custom field" in caplog.text

    def test_create_subtask_sends_parent_key(self):
        client = self._make_client()
        patcher, mock_client = _patch_httpx_post("TEST-3")
        with patcher:
            client.create_subtask(make_subtask(), "TEST-2")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["fields"]["parent"]["key"] == "TEST-2"
        assert payload["fields"]["issuetype"]["name"] == "Subtask"
