"""Tests cho database.py — dùng SQLite temp file."""
import os
from unittest.mock import patch

import pytest

from src.modules.database import (
    create_meeting,
    delete_meeting,
    delete_provider_config,
    get_meeting,
    get_provider_config,
    init_db,
    list_meetings,
    list_provider_configs,
    set_provider_config,
    update_meeting,
)
from src.schema import Epic, MeetingAnalysis, MeetingRecord, Priority, Task


def make_record(title: str = "Test meeting", with_analysis: bool = False) -> MeetingRecord:
    analysis = None
    if with_analysis:
        task = Task(summary="T1", assignee="Alice", deadline="2024-02-01", priority=Priority.HIGH, context="ctx")
        epic = Epic(summary="E1", description="desc", tasks=[task])
        analysis = MeetingAnalysis(epics=[epic], summary="summary")
    return MeetingRecord(title=title, transcript="transcript text", analysis=analysis)


@pytest.fixture()
def db(tmp_path) -> str:
    """Tạo SQLite DB tạm cho mỗi test, tự xóa sau khi xong."""
    db_file = str(tmp_path / "test_meetings.db")
    init_db(db_path=db_file)
    return db_file


class TestInitDb:
    def test_init_db_runs_without_error(self, tmp_path):
        db_file = str(tmp_path / "init_test.db")
        init_db(db_path=db_file)
        assert os.path.exists(db_file)


class TestCreateMeeting:
    def test_returns_positive_id(self, db):
        record = make_record()
        new_id = create_meeting(record, db_path=db)
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_stores_title_and_transcript(self, db):
        record = make_record("My Meeting")
        new_id = create_meeting(record, db_path=db)
        fetched = get_meeting(new_id, db_path=db)
        assert fetched.title == "My Meeting"
        assert fetched.transcript == "transcript text"

    def test_stores_analysis(self, db):
        record = make_record(with_analysis=True)
        new_id = create_meeting(record, db_path=db)
        fetched = get_meeting(new_id, db_path=db)
        assert fetched.analysis is not None
        assert fetched.analysis.summary == "summary"
        assert fetched.analysis.epics[0].tasks[0].priority == Priority.HIGH


class TestGetMeeting:
    def test_returns_none_for_missing_id(self, db):
        result = get_meeting(9999, db_path=db)
        assert result is None

    def test_id_set_on_fetched_record(self, db):
        record = make_record()
        new_id = create_meeting(record, db_path=db)
        fetched = get_meeting(new_id, db_path=db)
        assert fetched.id == new_id


class TestListMeetings:
    def test_empty_list_initially(self, db):
        assert list_meetings(db_path=db) == []

    def test_returns_all_records(self, db):
        create_meeting(make_record("M1"), db_path=db)
        create_meeting(make_record("M2"), db_path=db)
        records = list_meetings(db_path=db)
        assert len(records) == 2

    def test_newest_first(self, db):
        create_meeting(make_record("First"), db_path=db)
        create_meeting(make_record("Second"), db_path=db)
        records = list_meetings(db_path=db)
        titles = [r.title for r in records]
        assert titles.index("Second") < titles.index("First")


class TestUpdateMeeting:
    def test_update_title(self, db):
        record = make_record("Original")
        new_id = create_meeting(record, db_path=db)
        fetched = get_meeting(new_id, db_path=db)
        fetched.title = "Updated"
        update_meeting(fetched, db_path=db)
        refetched = get_meeting(new_id, db_path=db)
        assert refetched.title == "Updated"

    def test_update_raises_without_id(self, db):
        record = make_record()
        with pytest.raises(ValueError, match="id"):
            update_meeting(record, db_path=db)


class TestDeleteMeeting:
    def test_delete_removes_record(self, db):
        new_id = create_meeting(make_record(), db_path=db)
        delete_meeting(new_id, db_path=db)
        assert get_meeting(new_id, db_path=db) is None

    def test_delete_nonexistent_no_error(self, db):
        delete_meeting(9999, db_path=db)  # Không raise = OK


_FAKE_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # 32-byte base64 hợp lệ


class TestProviderConfigs:
    @pytest.fixture()
    def db_with_key(self, tmp_path):
        db_file = str(tmp_path / "test_prov.db")
        init_db(db_path=db_file)
        return db_file

    def _patch_key(self):
        return patch("src.modules.credential_vault.APP_SECRET_KEY", _FAKE_KEY)

    def test_set_and_get_roundtrip(self, db_with_key):
        config = {"base_url": "https://jira.test", "token": "abc123"}
        with self._patch_key():
            set_provider_config("jira", config, db_path=db_with_key)
            result = get_provider_config("jira", db_path=db_with_key)
        assert result == config

    def test_get_returns_none_when_not_set(self, db_with_key):
        with self._patch_key():
            result = get_provider_config("trello", db_path=db_with_key)
        assert result is None

    def test_set_upserts_on_conflict(self, db_with_key):
        with self._patch_key():
            set_provider_config("jira", {"token": "v1"}, db_path=db_with_key)
            set_provider_config("jira", {"token": "v2"}, db_path=db_with_key)
            result = get_provider_config("jira", db_path=db_with_key)
        assert result == {"token": "v2"}

    def test_list_returns_active_providers(self, db_with_key):
        with self._patch_key():
            set_provider_config("jira", {"token": "j"}, db_path=db_with_key)
            set_provider_config("trello", {"token": "t"}, db_path=db_with_key)
            names = list_provider_configs(db_path=db_with_key)
        assert set(names) == {"jira", "trello"}

    def test_delete_removes_config(self, db_with_key):
        with self._patch_key():
            set_provider_config("jira", {"token": "j"}, db_path=db_with_key)
            delete_provider_config("jira", db_path=db_with_key)
            result = get_provider_config("jira", db_path=db_with_key)
        assert result is None

    def test_migrate_schema_idempotent(self, tmp_path):
        """Gọi init_db nhiều lần không raise."""
        db_file = str(tmp_path / "idempotent.db")
        init_db(db_path=db_file)
        init_db(db_path=db_file)  # lần 2 không lỗi
        assert os.path.exists(db_file)


class TestCredentialVault:
    def test_encrypt_decrypt_roundtrip(self):
        with patch("src.modules.credential_vault.APP_SECRET_KEY", _FAKE_KEY):
            from src.modules.credential_vault import decrypt, encrypt
            ciphertext = encrypt("secret_value")
            assert ciphertext != "secret_value"
            assert decrypt(ciphertext) == "secret_value"

    def test_decrypt_raises_on_wrong_key(self):
        with patch("src.modules.credential_vault.APP_SECRET_KEY", _FAKE_KEY):
            from src.modules.credential_vault import encrypt
            ciphertext = encrypt("secret_value")

        other_key = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="
        with patch("src.modules.credential_vault.APP_SECRET_KEY", other_key):
            from src.modules.credential_vault import decrypt
            with pytest.raises(ValueError, match="decrypt"):
                decrypt(ciphertext)

    def test_raises_when_no_key_set(self):
        with patch("src.modules.credential_vault.APP_SECRET_KEY", None):
            from src.modules.credential_vault import encrypt
            with pytest.raises(ValueError, match="APP_SECRET_KEY"):
                encrypt("test")
