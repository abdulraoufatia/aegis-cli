"""Unit tests for atlasbridge.core.store.migrations — schema migration system."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest

from atlasbridge.core.store.database import Database
from atlasbridge.core.store.migrations import (
    LATEST_SCHEMA_VERSION,
    get_user_version,
    run_migrations,
)

# ---------------------------------------------------------------------------
# Helpers to simulate old database schemas
# ---------------------------------------------------------------------------

# Schema v0 ("pre-versioned") — audit_events and replies lack `timestamp`.
# This is the exact scenario that causes the reported crash.
_OLD_SCHEMA_NO_TIMESTAMP = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    tool        TEXT NOT NULL DEFAULT '',
    command     TEXT NOT NULL DEFAULT '',
    cwd         TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'starting',
    pid         INTEGER,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    exit_code   INTEGER
);

CREATE TABLE IF NOT EXISTS prompts (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL REFERENCES sessions(id),
    prompt_type         TEXT NOT NULL,
    confidence          TEXT NOT NULL,
    excerpt             TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'created',
    nonce               TEXT NOT NULL,
    nonce_used          INTEGER NOT NULL DEFAULT 0,
    expires_at          TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at         TEXT,
    response_normalized TEXT,
    channel_identity    TEXT
);

CREATE TABLE IF NOT EXISTS replies (
    id               TEXT PRIMARY KEY,
    prompt_id        TEXT NOT NULL REFERENCES prompts(id),
    session_id       TEXT NOT NULL,
    value            TEXT NOT NULL,
    channel_identity TEXT NOT NULL,
    nonce            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    session_id  TEXT NOT NULL DEFAULT '',
    prompt_id   TEXT NOT NULL DEFAULT '',
    payload     TEXT NOT NULL DEFAULT '{}'
);
"""

# Schema with the old `schema_version` table (pre-migration system)
_OLD_SCHEMA_WITH_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    tool        TEXT NOT NULL DEFAULT '',
    command     TEXT NOT NULL DEFAULT '',
    cwd         TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'starting',
    pid         INTEGER,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    exit_code   INTEGER
);

CREATE TABLE IF NOT EXISTS prompts (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL REFERENCES sessions(id),
    prompt_type         TEXT NOT NULL,
    confidence          TEXT NOT NULL,
    excerpt             TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'created',
    nonce               TEXT NOT NULL,
    nonce_used          INTEGER NOT NULL DEFAULT 0,
    expires_at          TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at         TEXT,
    response_normalized TEXT,
    channel_identity    TEXT
);

CREATE TABLE IF NOT EXISTS replies (
    id               TEXT PRIMARY KEY,
    prompt_id        TEXT NOT NULL REFERENCES prompts(id),
    session_id       TEXT NOT NULL,
    value            TEXT NOT NULL,
    channel_identity TEXT NOT NULL,
    nonce            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    session_id  TEXT NOT NULL DEFAULT '',
    prompt_id   TEXT NOT NULL DEFAULT '',
    payload     TEXT NOT NULL DEFAULT '{}'
);
"""

# Partial schema — only sessions table exists (simulates crash mid-DDL)
_PARTIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    tool        TEXT NOT NULL DEFAULT '',
    command     TEXT NOT NULL DEFAULT '',
    cwd         TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'starting',
    pid         INTEGER,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    exit_code   INTEGER
);
"""


def _create_old_db(tmp_path: Path, schema_sql: str) -> Path:
    """Create a SQLite DB with the given schema and return the path."""
    db_path = tmp_path / f"test_{uuid.uuid4().hex[:8]}.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema_sql)
    conn.close()
    return db_path


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for the given table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Tests: fresh install
# ---------------------------------------------------------------------------


class TestFreshInstall:
    def test_fresh_db_gets_all_tables(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "fresh.db")
        db.connect()

        conn = db._db
        for table in ("sessions", "prompts", "replies", "audit_events"):
            assert _table_exists(conn, table), f"table {table} should exist"

        db.close()

    def test_fresh_db_sets_user_version(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "fresh.db")
        db.connect()
        assert get_user_version(db._db) == LATEST_SCHEMA_VERSION
        db.close()

    def test_fresh_db_has_timestamp_columns(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "fresh.db")
        db.connect()

        assert "timestamp" in _column_names(db._db, "replies")
        assert "timestamp" in _column_names(db._db, "audit_events")
        db.close()

    def test_fresh_db_has_all_columns(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "fresh.db")
        db.connect()

        session_cols = _column_names(db._db, "sessions")
        assert "label" in session_cols
        assert "metadata" in session_cols

        prompt_cols = _column_names(db._db, "prompts")
        assert "channel_message_id" in prompt_cols
        assert "metadata" in prompt_cols

        audit_cols = _column_names(db._db, "audit_events")
        assert "prev_hash" in audit_cols
        assert "hash" in audit_cols

        db.close()

    def test_no_schema_version_table_on_fresh(self, tmp_path: Path) -> None:
        """The old schema_version table should not exist on fresh installs."""
        db = Database(tmp_path / "fresh.db")
        db.connect()
        assert not _table_exists(db._db, "schema_version")
        db.close()


# ---------------------------------------------------------------------------
# Tests: upgrade from old schema (the reported crash scenario)
# ---------------------------------------------------------------------------


class TestUpgradeFromOldSchema:
    def test_old_db_missing_timestamp_migrates_successfully(self, tmp_path: Path) -> None:
        """This is the exact crash scenario from the bug report."""
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)
        db = Database(db_path)
        db.connect()  # should NOT raise sqlite3.OperationalError

        assert "timestamp" in _column_names(db._db, "replies")
        assert "timestamp" in _column_names(db._db, "audit_events")
        assert get_user_version(db._db) == LATEST_SCHEMA_VERSION
        db.close()

    def test_old_db_missing_hash_columns_migrated(self, tmp_path: Path) -> None:
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)
        db = Database(db_path)
        db.connect()

        audit_cols = _column_names(db._db, "audit_events")
        assert "prev_hash" in audit_cols
        assert "hash" in audit_cols
        db.close()

    def test_old_db_missing_label_and_metadata_migrated(self, tmp_path: Path) -> None:
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)
        db = Database(db_path)
        db.connect()

        session_cols = _column_names(db._db, "sessions")
        assert "label" in session_cols
        assert "metadata" in session_cols
        db.close()

    def test_old_db_missing_prompt_columns_migrated(self, tmp_path: Path) -> None:
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)
        db = Database(db_path)
        db.connect()

        prompt_cols = _column_names(db._db, "prompts")
        assert "channel_message_id" in prompt_cols
        assert "metadata" in prompt_cols
        db.close()

    def test_old_db_existing_data_preserved(self, tmp_path: Path) -> None:
        """Existing rows should survive the migration."""
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)

        # Insert some data into the old schema
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO sessions (id, tool, command, cwd, status) "
            "VALUES ('sess-1', 'claude', '[\"claude\"]', '/tmp', 'running')"
        )
        conn.execute(
            "INSERT INTO audit_events (id, event_type, payload) "
            "VALUES ('evt-1', 'test_event', '{}')"
        )
        conn.commit()
        conn.close()

        # Migrate
        db = Database(db_path)
        db.connect()

        # Verify data is still there
        row = db.get_session("sess-1")
        assert row is not None
        assert row["tool"] == "claude"

        events = db.get_recent_audit_events(limit=1)
        assert len(events) == 1
        assert events[0]["event_type"] == "test_event"

        db.close()

    def test_schema_version_table_removed_after_migration(self, tmp_path: Path) -> None:
        """The old schema_version table should be dropped during migration."""
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_WITH_VERSION_TABLE)
        db = Database(db_path)
        db.connect()

        assert not _table_exists(db._db, "schema_version")
        assert get_user_version(db._db) == LATEST_SCHEMA_VERSION
        db.close()


# ---------------------------------------------------------------------------
# Tests: partial schema (crash during initial DDL)
# ---------------------------------------------------------------------------


class TestPartialSchema:
    def test_partial_db_completed_by_migration(self, tmp_path: Path) -> None:
        """If only sessions exists (crash mid-DDL), migration should create the rest."""
        db_path = _create_old_db(tmp_path, _PARTIAL_SCHEMA)
        db = Database(db_path)
        db.connect()

        for table in ("sessions", "prompts", "replies", "audit_events"):
            assert _table_exists(db._db, table), f"table {table} should exist"

        assert get_user_version(db._db) == LATEST_SCHEMA_VERSION
        db.close()


# ---------------------------------------------------------------------------
# Tests: idempotency (migration runs twice without error)
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_migration_idempotent_on_fresh_db(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "idempotent.db")
        db.connect()
        db.close()

        # Connect again — should be a no-op since already at latest version
        db2 = Database(tmp_path / "idempotent.db")
        db2.connect()
        assert get_user_version(db2._db) == LATEST_SCHEMA_VERSION
        db2.close()

    def test_migration_idempotent_on_upgraded_db(self, tmp_path: Path) -> None:
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)

        # First connect: migrates
        db = Database(db_path)
        db.connect()
        db.close()

        # Second connect: should be a no-op
        db2 = Database(db_path)
        db2.connect()
        assert get_user_version(db2._db) == LATEST_SCHEMA_VERSION
        db2.close()


# ---------------------------------------------------------------------------
# Tests: CRUD operations work after migration
# ---------------------------------------------------------------------------


class TestCRUDAfterMigration:
    def test_full_workflow_after_migration(self, tmp_path: Path) -> None:
        """All Database CRUD methods should work after migrating an old schema."""
        db_path = _create_old_db(tmp_path, _OLD_SCHEMA_NO_TIMESTAMP)
        db = Database(db_path)
        db.connect()

        # Save a session
        sid = str(uuid.uuid4())
        db.save_session(sid, tool="claude", command=["claude"], cwd="/tmp", label="test")

        # Save a prompt
        pid = str(uuid.uuid4())
        db.save_prompt(
            prompt_id=pid,
            session_id=sid,
            prompt_type="yes_no",
            confidence="high",
            excerpt="Continue?",
            nonce="test-nonce",
            expires_at="2099-12-31 23:59:59",
            channel_message_id="msg-1",
        )

        # Append an audit event (uses timestamp column)
        db.append_audit_event("evt-1", "test", {"key": "val"}, session_id=sid)

        # Read back
        session = db.get_session(sid)
        assert session["label"] == "test"

        prompt = db.get_prompt(pid)
        assert prompt["channel_message_id"] == "msg-1"

        events = db.get_recent_audit_events(limit=1)
        assert len(events) == 1
        assert events[0]["timestamp"] != ""

        db.close()


# ---------------------------------------------------------------------------
# Tests: run_migrations directly
# ---------------------------------------------------------------------------


class TestRunMigrationsDirect:
    def test_run_migrations_on_empty_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "direct.db"
        conn = sqlite3.connect(str(db_path))
        run_migrations(conn, db_path)
        assert get_user_version(conn) == LATEST_SCHEMA_VERSION
        conn.close()

    def test_future_version_raises(self, tmp_path: Path) -> None:
        db_path = tmp_path / "future.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION + 10}")
        with pytest.raises(RuntimeError, match="only supports up to"):
            run_migrations(conn, db_path)
        conn.close()

    def test_already_latest_is_noop(self, tmp_path: Path) -> None:
        db_path = tmp_path / "latest.db"
        conn = sqlite3.connect(str(db_path))
        run_migrations(conn, db_path)  # first run — migrates
        v1 = get_user_version(conn)
        run_migrations(conn, db_path)  # second run — no-op
        v2 = get_user_version(conn)
        assert v1 == v2 == LATEST_SCHEMA_VERSION
        conn.close()
