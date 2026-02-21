"""Unit tests for aegis.core.audit.writer — AuditWriter structured events."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from atlasbridge.core.audit.writer import AuditWriter
from atlasbridge.core.store.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "audit_test.db")
    d.connect()
    yield d
    d.close()


@pytest.fixture
def writer(db: Database) -> AuditWriter:
    return AuditWriter(db)


class TestAuditWriter:
    def test_session_started_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        writer.session_started(sid, "claude", ["claude", "--no-browser"])
        events = db.get_recent_audit_events(limit=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "session_started"
        assert events[0]["session_id"] == sid

    def test_session_ended_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        writer.session_ended(sid, exit_code=0, crashed=False)
        events = db.get_recent_audit_events(limit=1)
        assert events[0]["event_type"] == "session_ended"

    def test_prompt_detected_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        writer.prompt_detected(sid, pid, "yes_no", "high", excerpt="Continue?")
        events = db.get_recent_audit_events(limit=1)
        assert events[0]["event_type"] == "prompt_detected"
        assert events[0]["prompt_id"] == pid

    def test_hash_chain_integrity(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        writer.session_started(sid, "claude", ["claude"])
        writer.session_ended(sid, exit_code=0)
        events = db.get_recent_audit_events(limit=10)
        # Events come back newest first; reverse to check chain
        ordered = list(reversed(events))
        assert ordered[0]["prev_hash"] == ""  # genesis
        assert ordered[1]["prev_hash"] == ordered[0]["hash"]

    def test_reply_received_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        writer.reply_received(sid, pid, "telegram:123", "y", "abc123")
        events = db.get_recent_audit_events(limit=1)
        assert events[0]["event_type"] == "reply_received"

    def test_prompt_expired_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        writer.prompt_expired(sid, pid)
        events = db.get_recent_audit_events(limit=1)
        assert events[0]["event_type"] == "prompt_expired"

    def test_duplicate_callback_written(self, writer: AuditWriter, db: Database) -> None:
        sid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        writer.duplicate_callback(sid, pid, "nonce123")
        events = db.get_recent_audit_events(limit=1)
        assert events[0]["event_type"] == "duplicate_callback_ignored"
