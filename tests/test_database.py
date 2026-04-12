"""Tests cho database.py — dùng SQLite temp file."""
import os
import tempfile

import pytest

from src.modules.database import (
    create_meeting,
    delete_meeting,
    get_meeting,
    init_db,
    list_meetings,
    update_meeting,
)
from src.schema import Epic, MeetingAnalysis, MeetingRecord, Priority, Task


def make_record(title: str = "Test meeting", with_analysis: bool = False) -> MeetingRecord:
    analysis = None
    if with_analysis:
        task = Task("T1", "Alice", "2024-02-01", Priority.HIGH, "ctx")
        epic = Epic("E1", "desc", tasks=[task])
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
