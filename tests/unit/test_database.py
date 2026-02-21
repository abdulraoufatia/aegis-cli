"""Unit tests for aegis.core.store.database — Database CRUD and decide_prompt guard."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from atlasbridge.core.store.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.connect()
    yield d
    d.close()


def _sid() -> str:
    return str(uuid.uuid4())


def _expires_at(seconds: float = 600.0) -> str:
    # Use SQLite-compatible format (no T, no timezone suffix) so datetime('now') comparisons work
    dt = datetime.now(UTC) + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class TestSessionRepo:
    def test_save_and_get(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        row = db.get_session(sid)
        assert row is not None
        assert row["id"] == sid
        assert row["tool"] == "claude"

    def test_update_session(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        db.update_session(sid, status="completed", exit_code=0)
        row = db.get_session(sid)
        assert row["status"] == "completed"
        assert row["exit_code"] == 0

    def test_list_active(self, db: Database) -> None:
        s1, s2 = _sid(), _sid()
        db.save_session(s1, tool="claude", command=["claude"], cwd="/tmp")
        db.save_session(s2, tool="claude", command=["claude"], cwd="/tmp")
        db.update_session(s2, status="completed")
        active = db.list_active_sessions()
        ids = [r["id"] for r in active]
        assert s1 in ids
        assert s2 not in ids

    def test_get_missing(self, db: Database) -> None:
        assert db.get_session("nonexistent") is None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestPromptRepo:
    def _save_prompt(self, db: Database, sid: str, expires_in: float = 600.0) -> str:
        pid = str(uuid.uuid4())
        nonce = secrets.token_hex(16)
        db.save_prompt(
            prompt_id=pid,
            session_id=sid,
            prompt_type="yes_no",
            confidence="high",
            excerpt="Continue? (y/n)",
            nonce=nonce,
            expires_at=_expires_at(expires_in),
        )
        return pid, nonce

    def test_save_and_get(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        pid, nonce = self._save_prompt(db, sid)
        row = db.get_prompt(pid)
        assert row is not None
        assert row["nonce"] == nonce

    def test_decide_prompt_success(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        pid, nonce = self._save_prompt(db, sid)
        rows = db.decide_prompt(pid, "reply_received", "telegram:42", "y", nonce)
        assert rows == 1
        updated = db.get_prompt(pid)
        assert updated["status"] == "reply_received"
        assert updated["response_normalized"] == "y"
        assert updated["nonce_used"] == 1

    def test_decide_prompt_replay_rejected(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        pid, nonce = self._save_prompt(db, sid)
        db.decide_prompt(pid, "reply_received", "telegram:42", "y", nonce)
        rows = db.decide_prompt(pid, "reply_received", "telegram:42", "n", nonce)
        assert rows == 0

    def test_decide_prompt_expired_rejected(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        pid, nonce = self._save_prompt(db, sid, expires_in=-10)
        rows = db.decide_prompt(pid, "reply_received", "telegram:42", "y", nonce)
        assert rows == 0

    def test_decide_prompt_wrong_nonce_rejected(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        pid, nonce = self._save_prompt(db, sid)
        rows = db.decide_prompt(pid, "reply_received", "telegram:42", "y", "wrong-nonce")
        assert rows == 0

    def test_list_pending(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        p1, n1 = self._save_prompt(db, sid)
        p2, n2 = self._save_prompt(db, sid)
        db.decide_prompt(p2, "reply_received", "user", "y", n2)
        pending = db.list_pending_prompts(session_id=sid)
        ids = [r["id"] for r in pending]
        assert p1 in ids
        assert p2 not in ids

    def test_list_expired(self, db: Database) -> None:
        sid = _sid()
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp")
        exp_id, _ = self._save_prompt(db, sid, expires_in=-1)
        fresh_id, _ = self._save_prompt(db, sid, expires_in=600)
        expired_list = db.list_expired_pending()
        ids = [r["id"] for r in expired_list]
        assert exp_id in ids
        assert fresh_id not in ids


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_append_and_retrieve(self, db: Database) -> None:
        eid = str(uuid.uuid4())
        db.append_audit_event(eid, "test_event", {"key": "value"})
        events = db.get_recent_audit_events(limit=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"

    def test_hash_chain_prev_hash(self, db: Database) -> None:
        e1 = str(uuid.uuid4())
        e2 = str(uuid.uuid4())
        db.append_audit_event(e1, "first", {})
        db.append_audit_event(e2, "second", {})
        events = db.get_recent_audit_events(limit=10)
        # Most recent first; find both
        by_type = {e["event_type"]: e for e in events}
        assert by_type["second"]["prev_hash"] == by_type["first"]["hash"]

    def test_list_recent_limit(self, db: Database) -> None:
        for i in range(5):
            db.append_audit_event(str(uuid.uuid4()), f"ev_{i}", {})
        events = db.get_recent_audit_events(limit=3)
        assert len(events) == 3
